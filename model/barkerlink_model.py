"""BarkerLink fixed-point golden model.

THE GOLDEN MODEL IS LAW. The RTL is verified cycle/packet-for-packet against this
reference; on disagreement the spec arbitrates and this model is NEVER edited to make
RTL pass (model changes require a spec citation + DECISIONS entry). See docs/SPEC.md.

Scope (Phase 1): the full P0 DBPSK chain - 802.11 self-synchronizing scrambler
(z^-7 + z^-4 + 1), DBPSK differential encode, Barker-11 spread (4x oversample), a
4-bit soft-input 11-tap correlator with genie timing, differential demod, descramble,
and long-PLCP framing (SYNC / SFD 0xF3A0 / header SIGNAL+SERVICE+LENGTH+CRC-16 / PSDU)
plus internal loopback and a chip-flip noise channel. DQPSK (P1) symbol mapping is
included and unit-tested; its full spread/despread chain lands in Phase 5.

Conventions (these define the spec the RTL must meet):
  * Sign-bit domain: bit 0 == +1, bit 1 == -1, so value multiply == sign-bit XOR.
  * Barker-11 = (+1,-1,+1,+1,-1,+1,+1,+1,-1,-1,-1), leftmost chip transmitted first.
  * Fields are serialized MSB-first; PSDU bytes are serialized MSB-first.
  * LENGTH is the PSDU size in OCTETS (a documented digital-IP deviation from the
    802.11 microseconds field; DECISIONS D-0101).
  * Soft chips are 4-bit signed; loopback maps +1 chip -> +7, -1 chip -> -7 (SOFT_MAX).
  * Correlator accumulator is signed, width ACC_BITS, holds +/-(N_CHIPS*SOFT_MAX).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Constants (authoritative fixed-point / framing parameters)
# --------------------------------------------------------------------------- #
BARKER11 = (1, -1, 1, 1, -1, 1, 1, 1, -1, -1, -1)
BARKER_SIGNBITS = tuple(0 if c == 1 else 1 for c in BARKER11)  # +1->0, -1->1
N_CHIPS = 11
OVERSAMPLE = 4

SFD = 0xF3A0
SYNC_LEN = 128
SCRAMBLER_SEED = 0x6C          # non-degenerate 7-bit seed; 0x7F locks up on all-ones
                               # SYNC (feedback stuck at 0). Self-sync RX is
                               # seed-independent after 7 bits (DECISIONS D-0102).

SIGNAL_DBPSK_1M = 0x0A
SIGNAL_DQPSK_2M = 0x14
SERVICE_DEFAULT = 0x00

SOFT_MAX = 7                   # 4-bit signed soft-chip magnitude (range -8..+7)
ACC_BITS = 8                   # signed correlator accumulator width
CRC_POLY = 0x1021              # CRC-16-CCITT
CRC_INIT = 0xFFFF


# --------------------------------------------------------------------------- #
# Bit / byte helpers (MSB-first)
# --------------------------------------------------------------------------- #
def int_to_bits(value: int, width: int) -> list[int]:
    """MSB-first list of `width` bits."""
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def bits_to_int(bits: list[int]) -> int:
    v = 0
    for b in bits:
        v = (v << 1) | (b & 1)
    return v


def bytes_to_bits(data: bytes) -> list[int]:
    out: list[int] = []
    for byte in data:
        out.extend(int_to_bits(byte, 8))
    return out


def bits_to_bytes(bits: list[int]) -> bytes:
    assert len(bits) % 8 == 0, "bit count must be a multiple of 8"
    return bytes(bits_to_int(bits[i:i + 8]) for i in range(0, len(bits), 8))


# --------------------------------------------------------------------------- #
# Self-synchronizing scrambler / descrambler  (G(z) = z^-7 + z^-4 + 1)
# State register bit0 = z^-1 (newest) ... bit6 = z^-7. Feedback = z^-4 ^ z^-7.
# --------------------------------------------------------------------------- #
def _feedback(reg: int) -> int:
    return ((reg >> 3) & 1) ^ ((reg >> 6) & 1)   # z^-4 (bit3) ^ z^-7 (bit6)


class Scrambler:
    """Multiplicative scrambler: y[n] = x[n] ^ y[n-4] ^ y[n-7]; register holds y."""

    def __init__(self, seed: int = SCRAMBLER_SEED):
        self.reg = seed & 0x7F

    def scramble(self, bits: list[int]) -> list[int]:
        out = []
        for x in bits:
            y = x ^ _feedback(self.reg)
            self.reg = ((self.reg << 1) | y) & 0x7F   # feed back the OUTPUT
            out.append(y)
        return out


class Descrambler:
    """Self-sync descrambler: x[n] = y[n] ^ y[n-4] ^ y[n-7]; register holds y (input)."""

    def __init__(self, seed: int = SCRAMBLER_SEED):
        self.reg = seed & 0x7F

    def descramble(self, bits: list[int]) -> list[int]:
        out = []
        for y in bits:
            x = y ^ _feedback(self.reg)
            self.reg = ((self.reg << 1) | y) & 0x7F   # feed in the received bit
            out.append(x)
        return out


# --------------------------------------------------------------------------- #
# DBPSK differential encode / decode (e[n] = e[n-1] ^ b[n])
# --------------------------------------------------------------------------- #
def dbpsk_encode(bits: list[int], e0: int = 0) -> list[int]:
    e = e0
    out = []
    for b in bits:
        e ^= b
        out.append(e)
    return out


def dbpsk_decode(symbits: list[int], e0: int = 0) -> list[int]:
    prev = e0
    out = []
    for e in symbits:
        out.append(e ^ prev)
        prev = e
    return out


# --------------------------------------------------------------------------- #
# Barker spread / 4x oversample / genie despread (4-bit soft correlator)
# --------------------------------------------------------------------------- #
def spread_chiprate(symbits: list[int]) -> list[int]:
    """Each differential symbol bit -> 11 chip sign bits (e XOR barker)."""
    chips = []
    for e in symbits:
        for sb in BARKER_SIGNBITS:
            chips.append(e ^ sb)
    return chips


def oversample(chips: list[int], k: int = OVERSAMPLE) -> list[int]:
    out = []
    for c in chips:
        out.extend([c] * k)
    return out


def downsample_genie(stream: list[int], k: int = OVERSAMPLE, phase: int = 0) -> list[int]:
    return stream[phase::k]


def chips_to_soft(chips: list[int], soft_max: int = SOFT_MAX) -> list[int]:
    """Map 1-bit chips to 4-bit signed soft values (loopback): 0->+max, 1->-max."""
    return [soft_max if c == 0 else -soft_max for c in chips]


def despread_genie(soft_chips: list[int]) -> tuple[list[int], list[int]]:
    """Genie-timed 11-tap correlation. Returns (symbol sign bits, correlations)."""
    n_sym = len(soft_chips) // N_CHIPS
    symbits, corrs = [], []
    for s in range(n_sym):
        acc = 0
        base = s * N_CHIPS
        for k in range(N_CHIPS):
            acc += soft_chips[base + k] * BARKER11[k]
        symbits.append(0 if acc >= 0 else 1)   # +corr -> +1 (e=0), -corr -> -1 (e=1)
        corrs.append(acc)
    return symbits, corrs


# --------------------------------------------------------------------------- #
# Chip-flip noise channel (Bernoulli reference; RTL LFSR injector modeled in P5)
# --------------------------------------------------------------------------- #
def inject_chip_flips(chips: list[int], p: float, rng: random.Random) -> list[int]:
    return [c ^ (1 if rng.random() < p else 0) for c in chips]


# --------------------------------------------------------------------------- #
# CRC-16-CCITT over a bit list (MSB-first), init 0xFFFF, final complement.
# --------------------------------------------------------------------------- #
def crc16(bits: list[int]) -> int:
    crc = CRC_INIT
    for b in bits:
        msb = (crc >> 15) & 1
        crc = (crc << 1) & 0xFFFF
        if msb ^ (b & 1):
            crc ^= CRC_POLY
    return crc ^ 0xFFFF


# --------------------------------------------------------------------------- #
# Long-PLCP framing
# --------------------------------------------------------------------------- #
@dataclass
class PpduMeta:
    signal: int
    service: int
    length: int          # PSDU octets
    crc: int


def build_ppdu_bits(psdu: bytes, signal: int = SIGNAL_DBPSK_1M,
                    service: int = SERVICE_DEFAULT,
                    sync_len: int = SYNC_LEN) -> tuple[list[int], PpduMeta]:
    """Logical (pre-scramble) PPDU bit stream: SYNC | SFD | header | PSDU."""
    length = len(psdu)
    header_wo_crc = (int_to_bits(signal, 8) + int_to_bits(service, 8)
                     + int_to_bits(length, 16))
    crc = crc16(header_wo_crc)
    header = header_wo_crc + int_to_bits(crc, 16)
    bits = [1] * sync_len + int_to_bits(SFD, 16) + header + bytes_to_bits(psdu)
    return bits, PpduMeta(signal, service, length, crc)


@dataclass
class RxResult:
    sfd_found: bool
    crc_ok: bool
    meta: PpduMeta | None
    psdu: bytes
    sfd_index: int = -1


def parse_ppdu_bits(logical: list[int]) -> RxResult:
    """Find SFD in a descrambled logical bit stream, parse header, check CRC, slice PSDU."""
    sfd_pattern = int_to_bits(SFD, 16)
    idx = _find_pattern(logical, sfd_pattern)
    if idx < 0:
        return RxResult(False, False, None, b"", -1)
    hstart = idx + 16
    header = logical[hstart:hstart + 48]
    if len(header) < 48:
        return RxResult(True, False, None, b"", idx)
    signal = bits_to_int(header[0:8])
    service = bits_to_int(header[8:16])
    length = bits_to_int(header[16:32])
    rx_crc = bits_to_int(header[32:48])
    crc_ok = (crc16(header[0:32]) == rx_crc)
    meta = PpduMeta(signal, service, length, rx_crc)
    pstart = hstart + 48
    psdu_bits = logical[pstart:pstart + length * 8]
    psdu = bits_to_bytes(psdu_bits) if len(psdu_bits) == length * 8 else b""
    return RxResult(True, crc_ok, meta, psdu, idx)


def _find_pattern(bits: list[int], pattern: list[int]) -> int:
    n, m = len(bits), len(pattern)
    for i in range(n - m + 1):
        if bits[i:i + m] == pattern:
            return i
    return -1


# --------------------------------------------------------------------------- #
# Full DBPSK TX / RX and internal loopback
# --------------------------------------------------------------------------- #
def tx_dbpsk(psdu: bytes, signal: int = SIGNAL_DBPSK_1M,
             service: int = SERVICE_DEFAULT,
             sync_len: int = SYNC_LEN) -> tuple[list[int], PpduMeta]:
    """PSDU -> 1-bit chip stream (4x oversampled). Returns (stream, meta)."""
    logical, meta = build_ppdu_bits(psdu, signal, service, sync_len)
    scrambled = Scrambler().scramble(logical)
    symbits = dbpsk_encode(scrambled)
    return oversample(spread_chiprate(symbits)), meta


def rx_dbpsk(stream: list[int]) -> RxResult:
    """1-bit chip stream -> RxResult (genie chip timing: frame starts at sample 0)."""
    soft = chips_to_soft(downsample_genie(stream))
    symbits, _ = despread_genie(soft)
    scrambled = dbpsk_decode(symbits)
    logical = Descrambler().descramble(scrambled)
    return parse_ppdu_bits(logical)


def loopback_dbpsk(psdu: bytes, p_chip: float = 0.0, seed: int = 0,
                   signal: int = SIGNAL_DBPSK_1M,
                   sync_len: int = SYNC_LEN) -> RxResult:
    stream, _ = tx_dbpsk(psdu, signal=signal, sync_len=sync_len)
    if p_chip > 0.0:
        stream = inject_chip_flips(stream, p_chip, random.Random(seed))
    return rx_dbpsk(stream)


# --------------------------------------------------------------------------- #
# PHY-only DBPSK loopback for BER characterization (no scrambler/framing, chip-rate).
# Measures bit error at the post-differential-decode point, which is what the
# theoretical curve ber_dbpsk_bsc() predicts. (Descrambling multiplies errors x3,
# a separate, documented effect.)
# --------------------------------------------------------------------------- #
def phy_dbpsk_loopback(bits: list[int], p_chip: float, rng: random.Random) -> list[int]:
    sym = dbpsk_encode(bits)
    chips = spread_chiprate(sym)
    if p_chip > 0.0:
        chips = inject_chip_flips(chips, p_chip, rng)
    rx_sym, _ = despread_genie(chips_to_soft(chips))
    return dbpsk_decode(rx_sym)


# --------------------------------------------------------------------------- #
# DQPSK (P1) differential symbol mapping - Gray-coded dibit -> phase change.
# Full spread/despread chain lands in Phase 5; encode/decode are unit-tested now.
# --------------------------------------------------------------------------- #
# Gray mapping of (b1,b0) dibit to differential phase quadrant (units of 90 deg).
_DQPSK_ENC = {(0, 0): 0, (0, 1): 1, (1, 1): 2, (1, 0): 3}
_DQPSK_DEC = {v: k for k, v in _DQPSK_ENC.items()}


def dqpsk_encode(dibits: list[tuple[int, int]], q0: int = 0) -> list[int]:
    """Dibits -> absolute QPSK phase quadrants (0..3) via differential accumulation."""
    q = q0
    out = []
    for db in dibits:
        q = (q + _DQPSK_ENC[db]) & 3
        out.append(q)
    return out


def dqpsk_decode(quads: list[int], q0: int = 0) -> list[tuple[int, int]]:
    prev = q0
    out = []
    for q in quads:
        out.append(_DQPSK_DEC[(q - prev) & 3])
        prev = q
    return out
