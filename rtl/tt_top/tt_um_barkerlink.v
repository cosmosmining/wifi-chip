`default_nettype none
//============================================================================
// tt_um_barkerlink - Tiny Tapeout top wrapper for the BarkerLink DSSS baseband.
//
// Phase 0 scaffold: the standard TT pin interface plus a clean hierarchy down
// to barkerlink_core. The Phase 0 core is a synchronous registered datapath
// placeholder (ui_in -> uo_out) that validates clocking, active-low synchronous
// reset, the module hierarchy, and pin wiring end-to-end. The real SPI->APB3
// CSR bridge and TX/RX datapath replace the core internals in Phase 2
// (see docs/SPEC.md and docs/VPLAN.md). Pin map is finalized in SPEC.md.
//
// Target: sky130A, 2x2 TT tiles, single clock domain, f_clk = 50 MHz.
//============================================================================
module tt_um_barkerlink (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // bidirectional: input path
    output wire [7:0] uio_out,  // bidirectional: output path
    output wire [7:0] uio_oe,   // bidirectional: output enable (1=drive)
    input  wire       ena,      // design selected (held 1 while active)
    input  wire       clk,      // single clock domain from TT harness
    input  wire       rst_n     // active-low synchronous reset
);

  // ---- bidirectional pins ------------------------------------------------
  // Phase 0 leaves the uio bus configured as inputs (output enable low) and
  // drives the output path to a defined 0. Phase 2 maps SPI (CSR access) and
  // the IRQ/test-mode pins onto uio per the SPEC.md pin map.
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;       // 0 = high-Z input

  // ---- core instance -----------------------------------------------------
  barkerlink_core u_core (
      .clk      (clk),
      .rst_n    (rst_n),
      .ctrl_in  (ui_in),
      .stat_out (uo_out)
  );

  // ---- intentionally-unused Phase 0 inputs -------------------------------
  // ena and the uio input path are reserved for Phase 2 (test-enable CSR bit
  // and the SPI slave). Sunk here so lint stays warning-clean without a global
  // waiver; the sink is removed when these pins gain real loads. See DECISIONS.
  wire _unused = &{ena, uio_in, 1'b0};

endmodule
`default_nettype wire
