`default_nettype none
//============================================================================
// bl_correlator - genie-timed 11-tap soft Barker correlator + symbol decision.
//
// Consumes the 4x-oversampled 1-bit chip stream. Genie timing: samples oversample
// phase 0 (every 4th sample), so 11 samples form one symbol. Each sampled chip maps
// to a 4-bit soft value (+7 if chip==0, -7 if chip==1) and is correlated against the
// Barker sign (product = +7 if chip^barker_sb==0 else -7). The signed 8-bit
// accumulator holds the +/-77 peak; the symbol decision is its sign (acc<0 -> 1).
// Bit-accurate to model despread_genie(chips_to_soft(downsample_genie(.))); SPEC 6/8.
//============================================================================
module bl_correlator (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               in_valid,   // oversampled chip valid
    input  wire               in_chip,    // 1-bit oversampled chip
    output reg                out_valid,   // one pulse per symbol
    output reg                out_sym,     // decision bit (e)
    output reg  signed [7:0]  out_corr     // signed correlation peak
);
  localparam [10:0] BARKSB = 11'b11100010010;

  reg  [1:0]       phase;       // 0..3 oversample phase
  reg  [3:0]       chip_cnt;    // 0..10
  reg  signed [7:0] acc;

  wire              prod_neg = in_chip ^ BARKSB[chip_cnt];
  wire signed [7:0] contrib  = prod_neg ? -8'sd7 : 8'sd7;
  wire signed [7:0] sum      = acc + contrib;

  always @(posedge clk) begin
    if (!rst_n) begin
      phase <= 2'd0; chip_cnt <= 4'd0; acc <= 8'sd0;
      out_valid <= 1'b0; out_sym <= 1'b0; out_corr <= 8'sd0;
    end else begin
      out_valid <= 1'b0;
      if (in_valid) begin
        if (phase == 2'd0) begin
          if (chip_cnt == 4'd10) begin   // 11th sampled chip
            out_corr  <= sum;
            out_sym   <= sum[7];        // sign bit: 1 if negative
            out_valid <= 1'b1;
            acc       <= 8'sd0;
            chip_cnt  <= 4'd0;
          end else begin
            acc      <= sum;
            chip_cnt <= chip_cnt + 4'd1;
          end
        end
        phase <= (phase == 2'd3) ? 2'd0 : phase + 2'd1;   // 4x oversample
      end
    end
  end
endmodule
`default_nettype wire
