`default_nettype none
//============================================================================
// bl_noise - on-chip LFSR chip-flip noise injector (P1) for standalone BER curves.
//
// On each valid chip, a 16-bit Fibonacci LFSR (poly x^16+x^14+x^13+x^11+1) produces a
// pseudo-random word; the chip is flipped when en && (rnd < prob), i.e. with probability
// ~prob/65536. The flip uses the current LFSR word, then the LFSR advances. Bit-accurate
// to model.LfsrNoise. SPEC sec 12; CSR NOISE.PROB / CTRL.NOISE_EN.
//============================================================================
module bl_noise #(
    parameter [15:0] SEED = 16'hACE1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    input  wire [15:0] prob,
    input  wire        in_valid,
    input  wire        in_chip,
    output wire        out_valid,
    output wire        out_chip
);
  reg  [15:0] lfsr;
  wire        fb   = lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10];
  wire        flip = en && (lfsr < prob);

  always @(posedge clk) begin
    if (!rst_n)        lfsr <= SEED;
    else if (in_valid) lfsr <= {lfsr[14:0], fb};
  end

  assign out_valid = in_valid;
  assign out_chip  = in_chip ^ (in_valid ? flip : 1'b0);
endmodule
`default_nettype wire
