# BarkerLink — Verification Plan (VPLAN)

Every spec feature maps to **named test(s)** and **named functional coverage point(s)**.
A feature without coverage is unverified. Two test layers:

- **Model** — `model/test_model.py` pins the golden model (passing now, Phase 1).
- **RTL lockstep** — `dv/cocotb` benches compare RTL to the golden model cycle/packet
  (Phase 2), driven to ≥95% functional coverage over ≥500 seeds in Phase 3.

Status: `passing` / `wip` / `planned`.

## Coverage map

| ID | Feature (SPEC §) | Model test (now) | RTL bench (P2) | Coverage point(s) | Status |
|----|------------------|------------------|----------------|-------------------|--------|
| V-000 | Bring-up: clk/reset/hierarchy/pins | — | `test_smoke` ✓ | — | passing |
| V-TX-SCRAM | Scrambler z⁻⁷+z⁻⁴+1 (§7) | `test_scrambler_*` ✓ | `test_scrambler` | `cp_scram_state`, `cx_seed×data` | model✓ / rtl planned |
| V-TX-DBPSK | DBPSK diff encode (§7) | `test_dbpsk_diff_roundtrip` ✓ | `test_dbpsk` | `cp_dbpsk_transitions` | model✓ / rtl planned |
| V-TX-BARKER | Barker-11 spread + 4× (§7) | `test_spread_despread*`, `test_barker_*` ✓ | `test_spreader` | `cp_chip_phase` | model✓ / rtl planned |
| V-RX-CORR | 11-tap soft correlator (§8) | `test_spread_despread*` ✓ | `test_correlator` | `cp_corr_peak`, `cp_soft_levels` | model✓ / rtl planned |
| V-RX-PEAK | Peak/timing (§8) | (genie in model) | `test_peak` | `cp_peak_offset` | planned |
| V-RX-DEMOD | Diff demod + descramble (§8) | `test_loopback_*` ✓ | `test_rx_chain` | `cx_mode×noise` | model✓ / rtl planned |
| V-PLCP-SFD | SFD 0xF3A0 detect + false-detect (§9) | `test_plcp_build_parse*` ✓ | `test_plcp` | `cp_sfd_hit`, `cp_sfd_falsedet` | model✓ / rtl planned |
| V-PLCP-HDR | Header parse + CRC-16 (§9) | `test_plcp_*`, `test_crc16_*` ✓ | `test_plcp` | `cp_len`, `cp_crc_pass_fail` | model✓ / rtl planned |
| V-FIFO | TX/RX FIFO (§5) | — | `test_fifo` + formal | `cp_fifo_level`, `cp_full_empty` | planned |
| V-LOOP | Internal loopback packet (§12) | `test_loopback_no_noise_exact` ✓ | `test_loopback` (E2E) | `cx_len×data` | model✓ / rtl planned |
| V-BER | BER vs injected noise (§12,§14) | `test_phy_ber_tracks_theory`, `test_ber_theory_*` ✓ | `test_ber` (P5) | `cp_ber_band` | model✓ / rtl planned |
| V-CSR | APB3 CSR access (§5) | (RDL elaborates) | `test_csr` | `cp_reg_rw`, `cp_w1c` | planned |
| V-DQPSK | DQPSK 2 Mbps (§7, P1) | `test_dqpsk_diff_roundtrip` ✓ | `test_dqpsk` (P5) | `cp_dqpsk_quadrants` | model✓ / rtl P5 |
| V-NOISE | Noise injector LFSR (§12, P1) | — | `test_noise` (P5) | `cp_noise_prob` | planned |
| V-CCA | CCA/RSSI (§12, P1) | — | `test_cca` (P5) | `cp_cca_threshold` | planned |
| V-DFT | Scan + ATPG (§13, P6) | — | functional w/ scan | stuck-at % | planned |
| V-FP | Fixed-point widths (§6) | `test_fixedpoint_ranges` ✓ | (assert in benches) | `cp_acc_range` | model✓ |

## Closure gates
- **Phase 3 (P0):** 0 failures, **≥95% functional coverage** over **≥500** constrained-random
  seeds; coverage report committed.
- **Phase 5 (P1):** re-meet closure on expanded design; RTL BER-vs-injection within the
  ±1 dB-equivalent band of the golden model (`docs/img/ber_dbpsk.png`).

## Phase 1 status
Model layer **passing: 23/23** (`make model`). BER model tracks theory within ~10%
(`model/ber_curve.csv`). RTL benches land in Phase 2 alongside each module.
