`default_nettype none
//============================================================================
// Formal: descramble(scramble(x)) == x (self-synchronizing inverse).
// TX scrambler -> RX descrambler, matched seed, continuous feed. After the 2-cycle
// TX->RX pipeline fills, the descrambler output equals the input delayed by two.
//============================================================================
module scrambler_props (input wire clk);
  reg rst_n = 1'b0;
  always @(posedge clk) rst_n <= 1'b1;

  (* anyseq *) reg in_bit;
  wire in_valid = 1'b1;
  wire sc_v, sc_b, ds_v, ds_b;

  bl_scrambler #(.DESCRAMBLE(1'b0)) tx (
      .clk(clk), .rst_n(rst_n), .clear(1'b0),
      .in_valid(in_valid), .in_bit(in_bit), .out_valid(sc_v), .out_bit(sc_b));
  bl_scrambler #(.DESCRAMBLE(1'b1)) rx (
      .clk(clk), .rst_n(rst_n), .clear(1'b0),
      .in_valid(sc_v), .in_bit(sc_b), .out_valid(ds_v), .out_bit(ds_b));

  reg d1, d2;
  reg [1:0] fill;
  always @(posedge clk) begin
    if (!rst_n) begin
      d1 <= 1'b0; d2 <= 1'b0; fill <= 2'd0;
    end else begin
      d1 <= in_bit; d2 <= d1;
      if (fill != 2'd3) fill <= fill + 2'd1;
    end
  end

  always @(posedge clk) if (rst_n && fill == 2'd3) assert (ds_b == d2);
endmodule
`default_nettype wire
