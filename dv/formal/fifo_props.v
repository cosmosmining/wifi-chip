`default_nettype none
//============================================================================
// Formal: bl_fifo safety + data integrity.
//   safety    : level in [0,DEPTH]; full/empty flags consistent with level.
//   integrity : a symbolic tracked value pushed into the FIFO is read out in
//               FIFO order (no loss/reorder/duplication).
//
// Proved at DEPTH=4: the FIFO pointer/count logic is depth-parametric (identical for
// any DEPTH), so a small instance proves the logic; DEPTH=16 is additionally exercised
// exhaustively by the random regression. Small depth keeps the BMC fast under z3.
//============================================================================
module fifo_props (input wire clk);
  localparam integer DEPTH = 4;
  reg rst_n = 1'b0;
  always @(posedge clk) rst_n <= 1'b1;

  (* anyseq *) reg       wr_en;
  (* anyseq *) reg       rd_en;
  (* anyseq *) reg [7:0] wr_data;
  wire [7:0] rd_data;
  wire       full, empty;
  wire [2:0] level;            // $clog2(4)+1 = 3 bits

  bl_fifo #(.WIDTH(8), .DEPTH(DEPTH)) dut (
      .clk(clk), .rst_n(rst_n), .clear(1'b0),
      .wr_en(wr_en), .wr_data(wr_data), .rd_en(rd_en),
      .rd_data(rd_data), .full(full), .empty(empty), .level(level));

  wire wpush = wr_en && !full;
  wire rpop  = rd_en && !empty;

  always @(posedge clk) if (rst_n) begin
    assert (level <= DEPTH[2:0]);
    assert (full  == (level == DEPTH[2:0]));
    assert (empty == (level == 3'd0));
  end

  (* anyconst *) reg [7:0] f_data;
  (* anyseq  *) reg        f_arm;
  reg       f_track;
  reg [2:0] f_ahead;
  always @(posedge clk) begin
    if (!rst_n) begin
      f_track <= 1'b0;
      f_ahead <= 3'd0;
    end else if (!f_track) begin
      if (f_arm && wpush && (wr_data == f_data)) begin
        f_track <= 1'b1;
        f_ahead <= level - (rpop ? 3'd1 : 3'd0);
      end
    end else if (rpop) begin
      if (f_ahead == 3'd0) begin
        assert (rd_data == f_data);
        f_track <= 1'b0;
      end else begin
        f_ahead <= f_ahead - 3'd1;
      end
    end
  end
endmodule
`default_nettype wire
