`default_nettype none
//============================================================================
// bl_scrambler - 802.11 self-synchronizing scrambler/descrambler.
//
// G(z) = z^-7 + z^-4 + 1. State register lfsr[0] = z^-1 (newest) .. lfsr[6] = z^-7;
// feedback = lfsr[3] ^ lfsr[6] (z^-4 ^ z^-7). One bit per `in_valid` cycle; output is
// registered (1-cycle latency), out_valid tracks in_valid.
//
//   DESCRAMBLE=0 (TX): out = in ^ fb ; register shifts in the OUTPUT (scrambled) bit.
//   DESCRAMBLE=1 (RX): out = in ^ fb ; register shifts in the INPUT (received) bit, so
//                      it self-synchronizes within 7 bits regardless of seed.
//
// Bit-accurate to model/barkerlink_model.py {Scrambler,Descrambler}; SPEC sec 6/7.
//============================================================================
module bl_scrambler #(
    parameter [0:0] DESCRAMBLE = 1'b0,
    parameter [6:0] SEED       = 7'h6C
) (
    input  wire clk,
    input  wire rst_n,
    input  wire clear,        // synchronous re-seed to SEED
    input  wire in_valid,
    input  wire in_bit,
    output reg  out_valid,
    output reg  out_bit
);
  reg  [6:0] lfsr;
  wire       fb       = lfsr[3] ^ lfsr[6];
  wire       scr_bit  = in_bit ^ fb;
  wire       shift_in = DESCRAMBLE ? in_bit : scr_bit;

  always @(posedge clk) begin
    if (!rst_n) begin
      lfsr      <= SEED;
      out_valid <= 1'b0;
      out_bit   <= 1'b0;
    end else begin
      out_valid <= in_valid;
      if (clear) begin
        lfsr <= SEED;
      end else if (in_valid) begin
        out_bit <= scr_bit;
        lfsr    <= {lfsr[5:0], shift_in};
      end
    end
  end
endmodule
`default_nettype wire
