`default_nettype none
// DV-only wrapper: TX FIFO -> bl_tx -> (loopback chips) -> bl_rx, for the end-to-end
// datapath gate. The product loopback path (CTRL.LOOPBACK mux) lives in barkerlink_core.
module tb_loopback (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [7:0]  signal,
    input  wire [7:0]  service,
    input  wire [15:0] length,
    input  wire        tx_wr,        // push a PSDU byte into the TX FIFO
    input  wire [7:0]  tx_wr_data,
    output wire        tx_full,
    output wire        tx_busy,
    output wire        tx_done,
    output wire        sfd,
    output wire        crc_ok,
    output wire [7:0]  rx_signal,
    output wire [7:0]  rx_service,
    output wire [15:0] rx_length,
    output wire        byte_valid,
    output wire [7:0]  byte_data,
    output wire        rx_done
);
  wire        chip_valid, chip_out;
  wire [7:0]  fifo_head;
  wire        tx_pop;

  bl_fifo #(.WIDTH(8), .DEPTH(16)) u_txfifo (
      .clk(clk), .rst_n(rst_n), .clear(1'b0),
      .wr_en(tx_wr), .wr_data(tx_wr_data),
      .rd_en(tx_pop), .rd_data(fifo_head), .full(tx_full));

  bl_tx u_tx (
      .clk(clk), .rst_n(rst_n), .start(start),
      .signal(signal), .service(service), .length(length),
      .psdu_data(fifo_head), .psdu_pop(tx_pop),
      .busy(tx_busy), .done(tx_done),
      .chip_valid(chip_valid), .chip_out(chip_out));

  bl_rx u_rx (
      .clk(clk), .rst_n(rst_n), .in_valid(chip_valid), .in_chip(chip_out),
      .sfd(sfd), .crc_ok(crc_ok), .rx_signal(rx_signal), .rx_service(rx_service),
      .rx_length(rx_length), .byte_valid(byte_valid), .byte_data(byte_data),
      .done(rx_done));
endmodule
`default_nettype wire
