"""Unit tests for the BarkerLink golden model (and BER theory).

These pin down the reference behavior the RTL is held to in lockstep. Named tests
map to VPLAN.md entries.
"""
import random

import pytest

import barkerlink_model as bl
import ber_theory as bt


# --------------------------------------------------------------------------- #
# Scrambler / descrambler  (V-TX-SCRAM)
# --------------------------------------------------------------------------- #
def test_scrambler_descrambler_inverse_same_seed():
    rng = random.Random(1)
    bits = [rng.getrandbits(1) for _ in range(1000)]
    scr = bl.Scrambler().scramble(bits)
    rec = bl.Descrambler().descramble(scr)
    assert rec == bits


def test_descrambler_self_synchronizes_with_wrong_seed():
    rng = random.Random(2)
    bits = [rng.getrandbits(1) for _ in range(500)]
    scr = bl.Scrambler(seed=0x7F).scramble(bits)
    rec = bl.Descrambler(seed=0x00).descramble(scr)   # deliberately wrong seed
    # Self-synchronizing: correct from bit 7 onward regardless of initial state.
    assert rec[7:] == bits[7:]


def test_scrambler_is_not_identity():
    bits = [1] * 64
    assert bl.Scrambler().scramble(bits) != bits


# --------------------------------------------------------------------------- #
# DBPSK differential mapping  (V-TX-DBPSK)
# --------------------------------------------------------------------------- #
def test_dbpsk_diff_roundtrip():
    rng = random.Random(3)
    bits = [rng.getrandbits(1) for _ in range(777)]
    assert bl.dbpsk_decode(bl.dbpsk_encode(bits)) == bits


# --------------------------------------------------------------------------- #
# Barker spread / despread  (V-TX-BARKER, V-RX-CORR)
# --------------------------------------------------------------------------- #
def test_barker_autocorrelation_peak_is_eleven():
    assert sum(c * c for c in bl.BARKER11) == bl.N_CHIPS


def test_spread_despread_roundtrip_no_noise():
    rng = random.Random(4)
    symbits = [rng.getrandbits(1) for _ in range(300)]
    soft = bl.chips_to_soft(bl.spread_chiprate(symbits))
    rx, corrs = bl.despread_genie(soft)
    assert rx == symbits
    assert all(abs(c) == bl.N_CHIPS * bl.SOFT_MAX for c in corrs)  # clean peak


def test_oversample_downsample_inverse():
    chips = [0, 1, 1, 0, 1, 0, 0, 1]
    assert bl.downsample_genie(bl.oversample(chips)) == chips


# --------------------------------------------------------------------------- #
# CRC-16  (V-PLCP-HDR)
# --------------------------------------------------------------------------- #
def test_crc16_deterministic_and_detects_single_bit_flip():
    rng = random.Random(5)
    hdr = [rng.getrandbits(1) for _ in range(32)]
    c0 = bl.crc16(hdr)
    assert c0 == bl.crc16(hdr)                      # deterministic
    flipped = hdr[:]
    flipped[13] ^= 1
    assert bl.crc16(flipped) != c0                  # detects corruption


# --------------------------------------------------------------------------- #
# PLCP framing  (V-PLCP-SFD, V-PLCP-HDR)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("length", [0, 1, 7, 16, 63, 255])
def test_plcp_build_parse_roundtrip(length):
    rng = random.Random(100 + length)
    psdu = bytes(rng.getrandbits(8) for _ in range(length))
    bits, meta = bl.build_ppdu_bits(psdu)
    res = bl.parse_ppdu_bits(bits)
    assert res.sfd_found and res.crc_ok
    assert res.sfd_index == bl.SYNC_LEN
    assert res.meta.length == length
    assert res.meta.signal == bl.SIGNAL_DBPSK_1M
    assert res.psdu == psdu


# --------------------------------------------------------------------------- #
# Full DBPSK loopback  (V-LOOP)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("length", [0, 1, 20, 100])
def test_loopback_no_noise_exact(length):
    rng = random.Random(200 + length)
    psdu = bytes(rng.getrandbits(8) for _ in range(length))
    res = bl.loopback_dbpsk(psdu, p_chip=0.0)
    assert res.sfd_found and res.crc_ok and res.psdu == psdu


def test_noise_channel_extremes():
    chips = [0, 1, 0, 1, 1, 0]
    assert bl.inject_chip_flips(chips, 0.0, random.Random(0)) == chips
    assert bl.inject_chip_flips(chips, 1.0, random.Random(0)) == [c ^ 1 for c in chips]


# --------------------------------------------------------------------------- #
# BER vs theory  (V-BER) - statistical, generous tolerance
# --------------------------------------------------------------------------- #
def test_phy_ber_tracks_theory_at_p_025():
    p = 0.25
    ber, errors, bits = bt.simulate_ber_dbpsk(p, n_bits=80_000, seed=7,
                                              target_errors=400)
    theory = bt.ber_dbpsk_bsc(p)
    assert errors >= 100, f"too few errors ({errors}) for a stable estimate"
    assert abs(ber - theory) / theory < 0.30, f"MC {ber:.3e} vs theory {theory:.3e}"


def test_ber_theory_monotonic_and_bounded():
    assert bt.ber_dbpsk_bsc(0.0) == 0.0
    ps = [bt.ber_dbpsk_bsc(p) for p in (0.05, 0.10, 0.20, 0.30)]
    assert all(a < b for a, b in zip(ps, ps[1:]))   # increasing in p
    assert all(0.0 <= x <= 1.0 for x in ps)


# --------------------------------------------------------------------------- #
# DQPSK mapping (P1)  (V-TX-DBPSK / DQPSK)
# --------------------------------------------------------------------------- #
def test_dqpsk_diff_roundtrip():
    rng = random.Random(8)
    dibits = [(rng.getrandbits(1), rng.getrandbits(1)) for _ in range(400)]
    assert bl.dqpsk_decode(bl.dqpsk_encode(dibits)) == dibits


# --------------------------------------------------------------------------- #
# Fixed-point ranges (datapath widths the RTL must honor)
# --------------------------------------------------------------------------- #
def test_fixedpoint_ranges():
    assert -8 <= -bl.SOFT_MAX and bl.SOFT_MAX <= 7          # 4-bit signed soft chip
    assert 2 ** (bl.ACC_BITS - 1) > bl.N_CHIPS * bl.SOFT_MAX  # accumulator fits +/-77
    rng = random.Random(9)
    symbits = [rng.getrandbits(1) for _ in range(50)]
    _, corrs = bl.despread_genie(bl.chips_to_soft(bl.spread_chiprate(symbits)))
    assert all(-(2 ** (bl.ACC_BITS - 1)) <= c < 2 ** (bl.ACC_BITS - 1) for c in corrs)
