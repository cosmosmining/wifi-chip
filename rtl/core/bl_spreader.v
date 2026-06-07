`default_nettype none
//============================================================================
// bl_spreader - Barker-11 spreader with 4x oversample (valid/ready handshake).
//
// Accepts one DBPSK symbol bit (e) when `ready`, then emits 44 = 11 chips x 4
// oversample sign bits: chip[k] = e ^ barker_signbit[k], each repeated 4x.
// Barker sign bits (0=+1,1=-1), first chip first: 0,1,0,0,1,0,0,0,1,1,1.
// Bit-accurate to model oversample(spread_chiprate(.)); SPEC sec 6/7.
//============================================================================
module bl_spreader (
    input  wire clk,
    input  wire rst_n,
    input  wire in_valid,     // symbol available
    input  wire in_sym,       // differential symbol bit e
    output wire ready,        // high when idle, can accept a symbol
    output reg  out_valid,
    output reg  out_chip      // 1-bit oversampled chip sign
);
  localparam [5:0] TOT = 6'd44;           // 11 chips * 4 oversample
  localparam [10:0] BARKSB = 11'b11100010010;  // index i = sign bit of chip i

  reg        busy;
  reg  [5:0] cnt;             // 0..43
  reg        sym;
  wire [3:0] chip_idx = cnt[5:2];         // cnt / 4

  assign ready = !busy;

  always @(posedge clk) begin
    if (!rst_n) begin
      busy <= 1'b0; cnt <= 6'd0; sym <= 1'b0;
      out_valid <= 1'b0; out_chip <= 1'b0;
    end else if (!busy) begin
      out_valid <= 1'b0;
      if (in_valid) begin
        busy <= 1'b1; cnt <= 6'd0; sym <= in_sym;
      end
    end else begin
      out_valid <= 1'b1;
      out_chip  <= sym ^ BARKSB[chip_idx];
      if (cnt == TOT - 6'd1) begin
        busy <= 1'b0; cnt <= 6'd0;
      end else begin
        cnt <= cnt + 6'd1;
      end
    end
  end
endmodule
`default_nettype wire
