# BarkerLink — Verification Plan (VPLAN)

Every spec feature maps to **named test(s)** and **named functional coverage point(s)**.
A feature without coverage is unverified. This skeleton is filled out alongside `SPEC.md`
in Phase 1 and driven to closure in Phase 3 (≥95% functional coverage, ≥500 seeds).

## Legend
- **Test** — cocotb test id (`module::test_name`) or formal property id.
- **Cov** — functional coverage point id (`cp_*`) or cross (`cx_*`).
- **Status** — `planned` / `wip` / `passing` / `closed`.

## Coverage map

| ID | Feature (SPEC §) | Test(s) | Coverage point(s) | Status |
|----|------------------|---------|-------------------|--------|
| V-000 | Bring-up: clock/reset/hierarchy/pins (Phase 0) | `test_smoke::smoke_reset_and_datapath` | — | passing |
| V-TX-SCRAM | TX scrambler (§6) | _TBD-P1_ | `cp_scram_state`, `cx_scram_seed_x_data` | planned |
| V-TX-DBPSK | DBPSK differential encode (§6) | _TBD-P1_ | `cp_dbpsk_transitions` | planned |
| V-TX-BARKER | Barker-11 spread + 4× oversample (§6) | _TBD-P1_ | `cp_chip_phase` | planned |
| V-RX-CORR | 11-tap soft correlator (§7) | _TBD-P1_ | `cp_corr_peak`, `cp_soft_levels` | planned |
| V-RX-PEAK | Peak detect / timing (§7) | _TBD-P1_ | `cp_peak_offset` | planned |
| V-RX-DEMOD | Differential demod + descramble (§7) | _TBD-P1_ | `cx_mode_x_noise` | planned |
| V-PLCP-SFD | SFD detect 0xF3A0 + false-detect rate (§8) | _TBD-P1_ | `cp_sfd_hit`, `cp_sfd_falsedet` | planned |
| V-PLCP-HDR | Header parse + CRC-16 (§8) | _TBD-P1_ | `cp_len`, `cp_crc_pass_fail` | planned |
| V-FIFO | TX/RX FIFO (§9) | formal + `_TBD-P1` | `cp_fifo_level`, `cp_fifo_full_empty` | planned |
| V-LOOP | Internal loopback packet (§10) | _TBD-P1_ (E2E) | `cx_len_x_data` | planned |
| V-BER | BER vs injected noise (§10,§13) | _TBD-P1/P5_ | `cp_ber_band` | planned |
| V-DFT | Scan + ATPG (§11) | _TBD-P6_ | stuck-at % | planned |

## Closure gates
- **Phase 3 (P0):** 0 failures, ≥95% functional coverage over ≥500 constrained-random
  seeds; coverage report committed.
- **Phase 5 (P1):** re-meet closure on expanded design; RTL BER-vs-injection curve
  matches the golden model within the ±1 dB-equivalent band.
