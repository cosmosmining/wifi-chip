`default_nettype none
//============================================================================
// Formal: bl_fifo safety + data integrity.
//   safety    : level in [0,DEPTH]; full/empty flags consistent with level.
//   integrity : a symbolic tracked value pushed into the FIFO is read out in
//               FIFO order (no loss/reorder/duplication).
//============================================================================
module fifo_props (input wire clk);
  reg rst_n = 1'b0;
  always @(posedge clk) rst_n <= 1'b1;

  (* anyseq *) reg       wr_en;
  (* anyseq *) reg       rd_en;
  (* anyseq *) reg [7:0] wr_data;
  wire [7:0] rd_data;
  wire       full, empty;
  wire [4:0] level;

  bl_fifo #(.WIDTH(8), .DEPTH(16)) dut (
      .clk(clk), .rst_n(rst_n), .clear(1'b0),
      .wr_en(wr_en), .wr_data(wr_data), .rd_en(rd_en),
      .rd_data(rd_data), .full(full), .empty(empty), .level(level));

  wire wpush = wr_en && !full;
  wire rpop  = rd_en && !empty;

  always @(posedge clk) if (rst_n) begin
    assert (level <= 5'd16);
    assert (full  == (level == 5'd16));
    assert (empty == (level == 5'd0));
  end

  (* anyconst *) reg [7:0] f_data;
  (* anyseq  *) reg        f_arm;
  reg        f_track;
  reg [4:0]  f_ahead;
  always @(posedge clk) begin
    if (!rst_n) begin
      f_track <= 1'b0;
      f_ahead <= 5'd0;
    end else if (!f_track) begin
      if (f_arm && wpush && (wr_data == f_data)) begin
        f_track <= 1'b1;
        f_ahead <= level - (rpop ? 5'd1 : 5'd0);
      end
    end else if (rpop) begin
      if (f_ahead == 5'd0) begin
        assert (rd_data == f_data);
        f_track <= 1'b0;
      end else begin
        f_ahead <= f_ahead - 5'd1;
      end
    end
  end
endmodule
`default_nettype wire
