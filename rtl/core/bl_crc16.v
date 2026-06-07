`default_nettype none
//============================================================================
// bl_crc16 - streaming CRC-16-CCITT (poly 0x1021), MSB-first, init 0xFFFF,
// result complemented. `clear` re-seeds to 0xFFFF; one bit per in_valid.
// crc_out is the transmit/compare value (complemented running CRC).
// Bit-accurate to model crc16(); SPEC sec 9 (D-0103).
//============================================================================
module bl_crc16 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clear,
    input  wire        in_valid,
    input  wire        in_bit,
    output wire [15:0] crc_out
);
  reg  [15:0] crc;
  wire        fb = crc[15] ^ in_bit;

  always @(posedge clk) begin
    if (!rst_n)
      crc <= 16'hFFFF;
    else if (clear)
      crc <= 16'hFFFF;
    else if (in_valid)
      crc <= {crc[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
  end

  assign crc_out = crc ^ 16'hFFFF;
endmodule
`default_nettype wire
