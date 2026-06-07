`default_nettype none
// DV-only wrapper: wires bl_tx's chip stream straight into bl_rx (internal loopback)
// for the Phase 2 end-to-end gate. The product loopback path (CTRL.LOOPBACK mux) lands
// with the host integration; this exercises the full TX+RX datapath concurrently.
module tb_loopback (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [7:0]  signal,
    input  wire [7:0]  service,
    input  wire [15:0] length,
    input  wire [7:0]  psdu_data,
    output wire [15:0] psdu_addr,
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
  wire chip_valid, chip_out;

  bl_tx u_tx (
      .clk(clk), .rst_n(rst_n), .start(start),
      .signal(signal), .service(service), .length(length),
      .psdu_data(psdu_data), .psdu_addr(psdu_addr),
      .busy(tx_busy), .done(tx_done),
      .chip_valid(chip_valid), .chip_out(chip_out));

  bl_rx u_rx (
      .clk(clk), .rst_n(rst_n), .in_valid(chip_valid), .in_chip(chip_out),
      .sfd(sfd), .crc_ok(crc_ok), .rx_signal(rx_signal), .rx_service(rx_service),
      .rx_length(rx_length), .byte_valid(byte_valid), .byte_data(byte_data),
      .done(rx_done));
endmodule
`default_nettype wire
