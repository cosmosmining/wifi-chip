"""Phase 3 constrained-random regression + functional coverage (V-* points).

One cocotb test, two modes (selected by BL_MODE so each build runs the right path against
its own toplevel; the runner's testcase filter is unreliable here):
  lb  : full chip (TX FIFO -> bl_tx -> internal loopback -> bl_rx), SEEDS random packets,
        NOISELESS -> exact PSDU recovery + RTL==model.
  rxn : model TX + seeded chip flips -> RTL bl_rx vs model rx (lockstep under noise),
        exercising the CRC-fail / noise coverage bins.
Both modes share one coverage DB (build/cov/coverage.json).

SYNC_LEN is shortened to 24 for sim throughput (taped-out value 128; preamble length does
not change the logic under test - DECISIONS D-0111). `make regress` (SEEDS overridable),
`make cov` reports/gates coverage.
"""
import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

import bl_paths
import barkerlink_model as bl
from bl_coverage import Coverage

CLK = bl_paths.CLK_PERIOD_NS
SYNC = int(os.environ.get("BL_SYNC", "24"))
SEEDS = int(os.environ.get("SEEDS", "500"))
NOISE_SEEDS = int(os.environ.get("NOISE_SEEDS", "60"))
MAXLEN = 24


async def _run_loopback(dut, psdu, service):
    dut.start.value = 0
    dut.tx_wr.value = 0
    dut.tx_wr_data.value = 0
    dut.signal.value = bl.SIGNAL_DBPSK_1M
    dut.service.value = service
    dut.length.value = len(psdu)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut.start.value = 1
    await ClockCycles(dut.clk, 1)
    dut.start.value = 0

    got = bytearray()
    pushed = 0
    saw_full = False
    for _ in range((88 + len(psdu) * 8) * 60 + 4000):
        if pushed < len(psdu) and not int(dut.tx_full.value):
            dut.tx_wr.value = 1
            dut.tx_wr_data.value = psdu[pushed]
            pushed += 1
        else:
            dut.tx_wr.value = 0
        if int(dut.tx_full.value):
            saw_full = True
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if int(dut.byte_valid.value):
            got.append(int(dut.byte_data.value))
        if int(dut.rx_done.value):
            break
    dut.tx_wr.value = 0
    return bytes(got), int(dut.crc_ok.value), saw_full


async def _do_loopback(dut):
    cov = Coverage()
    rng = random.Random(0xB17)
    for s in range(SEEDS):
        length = rng.randint(1, MAXLEN)
        psdu = bytes(rng.getrandbits(8) for _ in range(length))
        service = rng.choice([0, rng.randint(1, 255)])
        got, crc_ok, saw_full = await _run_loopback(dut, psdu, service)
        assert crc_ok == 1, f"seed {s} len {length}: CRC not OK"
        assert got == psdu, f"seed {s} len {length}: {got.hex()} != {psdu.hex()}"
        m = bl.loopback_dbpsk(psdu, p_chip=0.0, sync_len=SYNC)
        assert m.crc_ok and m.psdu == psdu, f"seed {s}: model disagrees"
        cov.sample_packet(length, psdu, service, 0.0, True, saw_full, True)
    cov.save()
    dut._log.info("regress lb OK over %d seeds", SEEDS)


async def _feed_rx(dut, stream):
    dut.in_valid.value = 0
    dut.in_chip.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    got = bytearray()
    sfd_seen = False
    for c in list(stream) + [0] * 80:     # tail to flush pipeline + parse
        dut.in_valid.value = 1 if c is not None else 0
        dut.in_chip.value = c
        await ClockCycles(dut.clk, 1)
        await Timer(1, unit="ns")
        if int(dut.sfd.value):
            sfd_seen = True
        if int(dut.byte_valid.value):
            got.append(int(dut.byte_data.value))
    dut.in_valid.value = 0
    return bytes(got), int(dut.crc_ok.value), sfd_seen, int(dut.rx_length.value)


async def _do_rxnoise(dut):
    cov = Coverage()
    rng = random.Random(0x501)
    levels = [0.0, 0.03, 0.20]
    for s in range(NOISE_SEEDS):
        length = rng.randint(1, MAXLEN)
        psdu = bytes(rng.getrandbits(8) for _ in range(length))
        p = levels[s % len(levels)]
        stream, _ = bl.tx_dbpsk(psdu, sync_len=SYNC)
        if p > 0:
            stream = bl.inject_chip_flips(stream, p, random.Random(0xC0FFEE + s))
        got, crc_ok, sfd_seen, rxlen = await _feed_rx(dut, stream)
        m = bl.rx_dbpsk(stream)
        assert sfd_seen == m.sfd_found, f"seed {s}: SFD {sfd_seen} != model {m.sfd_found}"
        assert bool(crc_ok) == m.crc_ok, f"seed {s}: crc {crc_ok} != model {m.crc_ok}"
        if m.crc_ok:
            assert rxlen == m.meta.length and got == m.psdu, f"seed {s}: payload mismatch"
        cov.sample_packet(length, psdu, 0, p, bool(crc_ok), False, sfd_seen)
    cov.save()
    dut._log.info("regress rxn OK over %d seeds", NOISE_SEEDS)


@cocotb.test()
async def regress(dut):
    cocotb.start_soon(Clock(dut.clk, CLK, unit="ns").start())
    if os.environ.get("BL_MODE", "lb") == "lb":
        await _do_loopback(dut)
    else:
        await _do_rxnoise(dut)


def _run(top, sources, mode, params=None):
    from cocotb_tools.runner import get_runner, get_results
    bdir = bl_paths.build_dir(f"regress_{mode}")
    runner = get_runner("icarus")
    runner.build(sources=sources, hdl_toplevel=top, parameters=params or {},
                 timescale=bl_paths.TIMESCALE, build_dir=str(bdir), always=True)
    xml = runner.test(hdl_toplevel=top, test_module="test_regress",
                      test_dir=str(bl_paths.COCOTB_DIR), build_dir=str(bdir),
                      extra_env={"BL_MODE": mode}, results_xml=str(bdir / "r.xml"))
    _, failed = get_results(xml)
    assert failed == 0


def test_regress_loopback():
    sources = sorted((bl_paths.RTL_DIR / "core").glob("*.v")) + \
        [bl_paths.COCOTB_DIR / "tb_loopback.v"]
    _run("tb_loopback", sources, "lb", {"SYNC_LEN": SYNC})


def test_regress_rx_noise():
    core = bl_paths.RTL_DIR / "core"
    sources = [core / "bl_rx.v", core / "bl_correlator.v", core / "bl_dbpsk.v",
               core / "bl_scrambler.v", core / "bl_crc16.v"]
    _run("bl_rx", sources, "rxn")
