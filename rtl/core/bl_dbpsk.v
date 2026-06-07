`default_nettype none
//============================================================================
// bl_dbpsk - DBPSK differential encoder / decoder (streaming, 1 bit / in_valid).
//
//   ENCODE (DECODE=0): e[n] = e[n-1] ^ b[n]        (state holds e, fed by result)
//   DECODE (DECODE=1): b[n] = e[n] ^ e[n-1]        (state holds prev e, fed by input)
//
// Both reduce to: result = in ^ state ; next_state = DECODE ? in : result.
// Reset reference e[-1] = 0 (matches model dbpsk_encode/decode e0=0). SPEC sec 7/8.
//============================================================================
module bl_dbpsk #(
    parameter [0:0] DECODE = 1'b0
) (
    input  wire clk,
    input  wire rst_n,
    input  wire clear,        // synchronous reset of the differential reference
    input  wire in_valid,
    input  wire in_bit,
    output reg  out_valid,
    output reg  out_bit
);
  reg  state;
  wire result = in_bit ^ state;
  wire nstate = DECODE ? in_bit : result;

  always @(posedge clk) begin
    if (!rst_n) begin
      state     <= 1'b0;
      out_valid <= 1'b0;
      out_bit   <= 1'b0;
    end else begin
      out_valid <= in_valid;
      if (clear) begin
        state <= 1'b0;
      end else if (in_valid) begin
        out_bit <= result;
        state   <= nstate;
      end
    end
  end
endmodule
`default_nettype wire
