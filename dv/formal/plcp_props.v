`default_nettype none
//============================================================================
// Formal: bl_rx PLCP FSM legal transitions + no-deadlock (DONE always returns to
// SEARCH next cycle). State encoding: SEARCH=0, HDR=1, PSDU=2, DONE=3.
//============================================================================
module plcp_props (input wire clk);
  reg rst_n = 1'b0;
  always @(posedge clk) rst_n <= 1'b1;

  (* anyseq *) reg in_valid, in_chip;
  wire        sfd, crc_ok, crc_err, byte_valid, rx_done;
  wire [7:0]  rx_signal, rx_service, byte_data;
  wire [15:0] rx_length;
  wire [1:0]  st;

  bl_rx dut (
      .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_chip(in_chip),
      .sfd(sfd), .crc_ok(crc_ok), .crc_err(crc_err),
      .rx_signal(rx_signal), .rx_service(rx_service), .rx_length(rx_length),
      .byte_valid(byte_valid), .byte_data(byte_data), .done(rx_done),
      .f_state(st));

  reg [1:0] pst;
  reg       pv;
  always @(posedge clk) begin
    pst <= st;
    pv  <= rst_n;
  end

  always @(posedge clk) if (rst_n && pv) begin
    case (pst)
      2'd0: assert (st == 2'd0 || st == 2'd1);
      2'd1: assert (st == 2'd1 || st == 2'd2 || st == 2'd0);
      2'd2: assert (st == 2'd2 || st == 2'd3);
      2'd3: assert (st == 2'd0);
    endcase
  end
endmodule
`default_nettype wire
