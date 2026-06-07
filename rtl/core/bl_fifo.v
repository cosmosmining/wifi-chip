`default_nettype none
//============================================================================
// bl_fifo - synchronous flop-based FIFO (first-word-fall-through read).
// rd_data always shows the head; rd_en pops it. No data is stored in SRAM.
// Depth <= 16 per project rule. Used for TX/RX PSDU byte buffering.
//============================================================================
module bl_fifo #(
    parameter integer WIDTH = 8,
    parameter integer DEPTH = 16
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             clear,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    input  wire             rd_en,
    output wire [WIDTH-1:0] rd_data,
    output wire             full,
    output wire             empty,
    output wire [$clog2(DEPTH):0] level
);
  localparam integer AW = $clog2(DEPTH);

  reg [WIDTH-1:0] mem [0:DEPTH-1];
  reg [AW-1:0]    wptr, rptr;
  reg [AW:0]      cnt;

  assign full    = (cnt == DEPTH[AW:0]);
  assign empty   = (cnt == {(AW+1){1'b0}});
  assign level   = cnt;
  assign rd_data = mem[rptr];

  wire do_wr = wr_en && !full;
  wire do_rd = rd_en && !empty;

  always @(posedge clk) begin
    if (!rst_n) begin
      wptr <= {AW{1'b0}}; rptr <= {AW{1'b0}}; cnt <= {(AW+1){1'b0}};
    end else if (clear) begin
      wptr <= {AW{1'b0}}; rptr <= {AW{1'b0}}; cnt <= {(AW+1){1'b0}};
    end else begin
      if (do_wr) begin
        mem[wptr] <= wr_data;
        wptr <= (wptr == DEPTH[AW-1:0]-1'b1) ? {AW{1'b0}} : wptr + 1'b1;
      end
      if (do_rd) begin
        rptr <= (rptr == DEPTH[AW-1:0]-1'b1) ? {AW{1'b0}} : rptr + 1'b1;
      end
      case ({do_wr, do_rd})
        2'b10:   cnt <= cnt + 1'b1;
        2'b01:   cnt <= cnt - 1'b1;
        default: cnt <= cnt;
      endcase
    end
  end
endmodule
`default_nettype wire
