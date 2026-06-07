`default_nettype none
//============================================================================
// barkerlink_core - bus-facing BarkerLink IP (Phase 0 scaffold).
//
// Phase 0: a synchronous, active-low-reset registered passthrough that proves
// out the clock / reset / datapath / hierarchy end-to-end. Phase 2 replaces
// the internals with the APB3 CSR block, the TX datapath (scrambler / DBPSK /
// Barker-11 spreader) and the RX datapath (soft correlator / peak detect /
// differential demod / descrambler) per docs/SPEC.md. The port list will grow
// accordingly (SPI/APB, FIFO, IRQ); this stub deliberately keeps the minimal
// clocked surface so the smoke bench can verify data motion through hierarchy.
//============================================================================
module barkerlink_core (
    input  wire       clk,
    input  wire       rst_n,    // active-low, synchronous
    input  wire [7:0] ctrl_in,  // Phase 0 placeholder data in  (TT ui_in)
    output reg  [7:0] stat_out  // Phase 0 placeholder data out (TT uo_out)
);

  // Synchronous reset, no latches, single edge. Registered passthrough is a
  // placeholder datapath: it confirms the clock edge, the active-low sync
  // reset, and that data actually traverses the hierarchy to the pins.
  always @(posedge clk) begin
    if (!rst_n)
      stat_out <= 8'h00;
    else
      stat_out <= ctrl_in;
  end

endmodule
`default_nettype wire
