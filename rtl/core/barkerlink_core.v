`default_nettype none
//============================================================================
// barkerlink_core - bus-facing BarkerLink IP (Phase 2 integration).
//
// APB3 CSR + TX/RX byte FIFOs + TX datapath (bl_tx) + RX datapath (bl_rx) +
// internal loopback mux + IRQ aggregation. Host pushes PSDU to TX_FIFO, pulses
// CTRL.TX_START; chips egress on tx_chip (and, with CTRL.LOOPBACK, fold back into
// RX). RX writes recovered PSDU to RX_FIFO; the host drains it via RX_FIFO reads.
// CCA / RSSI / noise injector are P1 (tied off here). SPEC sec 5/7/8/9/12.
//============================================================================
module barkerlink_core (
    input  wire        clk,
    input  wire        rst_n,
    // APB3 (driven by the SPI->APB bridge)
    input  wire        psel,
    input  wire        penable,
    input  wire        pwrite,
    input  wire [7:0]  paddr,
    input  wire [31:0] pwdata,
    output wire [31:0] prdata,
    output wire        pready,
    // chip-stream pins
    output wire        tx_chip,
    output wire        tx_chip_valid,
    input  wire        rx_chip_ext,
    input  wire        rx_chip_valid_ext,
    // sideband
    output wire        irq,
    output wire        cca,
    output wire        scan_en,
    output wire        test_mode,
    output wire        sfd_det,
    output wire        crc_ok
);
  // --- CSR control/status nets ---
  wire        ctrl_en, ctrl_rx_en, ctrl_loopback, ctrl_mode, ctrl_noise_en;
  wire        tx_start, soft_rst;
  wire [7:0]  cfg_signal, cfg_service;
  wire [15:0] cfg_length;
  wire [15:0] noise_prob;     // P1 (unused)
  wire [7:0]  cca_thresh;     // P1 (unused)
  wire        tx_fifo_wr;
  wire [7:0]  tx_fifo_wdata;
  wire        rx_fifo_rd;

  wire [7:0]  tx_head, rx_head;
  wire        tx_full, tx_empty, rx_full, rx_empty;
  wire [4:0]  tx_level, rx_level;

  // --- TX datapath ---
  wire        tx_pop, tx_busy, tx_done, tx_cv, tx_c;
  bl_fifo #(.WIDTH(8), .DEPTH(16)) u_txfifo (
      .clk(clk), .rst_n(rst_n), .clear(soft_rst),
      .wr_en(tx_fifo_wr), .wr_data(tx_fifo_wdata),
      .rd_en(tx_pop), .rd_data(tx_head),
      .full(tx_full), .empty(tx_empty), .level(tx_level));

  bl_tx u_tx (
      .clk(clk), .rst_n(rst_n), .start(tx_start & ctrl_en),
      .signal(cfg_signal), .service(cfg_service), .length(cfg_length),
      .psdu_data(tx_head), .psdu_pop(tx_pop),
      .busy(tx_busy), .done(tx_done),
      .chip_valid(tx_cv), .chip_out(tx_c));

  assign tx_chip       = tx_c;
  assign tx_chip_valid = tx_cv;

  // --- loopback mux (internal TX chips, or external RX pins) ---
  wire rx_c  = ctrl_loopback ? tx_c  : rx_chip_ext;
  wire rx_cv = (ctrl_loopback ? tx_cv : rx_chip_valid_ext) & ctrl_rx_en;

  // --- RX datapath ---
  wire        rx_sfd, rx_crc_ok, rx_crc_err, rx_byte_valid, rx_done;
  wire [7:0]  rx_byte_data, rx_sig, rx_svc;
  wire [15:0] rx_len;
  bl_rx u_rx (
      .clk(clk), .rst_n(rst_n), .in_valid(rx_cv), .in_chip(rx_c),
      .sfd(rx_sfd), .crc_ok(rx_crc_ok), .crc_err(rx_crc_err),
      .rx_signal(rx_sig), .rx_service(rx_svc), .rx_length(rx_len),
      .byte_valid(rx_byte_valid), .byte_data(rx_byte_data), .done(rx_done));

  bl_fifo #(.WIDTH(8), .DEPTH(16)) u_rxfifo (
      .clk(clk), .rst_n(rst_n), .clear(soft_rst),
      .wr_en(rx_byte_valid), .wr_data(rx_byte_data),
      .rd_en(rx_fifo_rd), .rd_data(rx_head),
      .full(rx_full), .empty(rx_empty), .level(rx_level));

  // --- status: latch SFD seen; CRC ok is a level from bl_rx ---
  reg sfd_seen;
  always @(posedge clk) begin
    if (!rst_n)        sfd_seen <= 1'b0;
    else if (soft_rst) sfd_seen <= 1'b0;
    else if (rx_sfd)   sfd_seen <= 1'b1;
  end
  assign sfd_det = sfd_seen;
  assign crc_ok  = rx_crc_ok;
  assign cca     = 1'b0;   // P1

  // --- IRQ event vector: [0]tx_done [1]rx_done [2]sfd [3]crc_err [4]rx_fifo [5]cca ---
  wire [5:0] irq_set = {1'b0, rx_byte_valid, rx_crc_err, rx_sfd, rx_done, tx_done};

  bl_csr u_csr (
      .clk(clk), .rst_n(rst_n),
      .psel(psel), .penable(penable), .pwrite(pwrite),
      .paddr(paddr), .pwdata(pwdata), .prdata(prdata), .pready(pready), .irq(irq),
      .ctrl_en(ctrl_en), .ctrl_rx_en(ctrl_rx_en), .ctrl_loopback(ctrl_loopback),
      .ctrl_mode(ctrl_mode), .ctrl_noise_en(ctrl_noise_en),
      .tx_start(tx_start), .soft_rst(soft_rst),
      .cfg_signal(cfg_signal), .cfg_service(cfg_service), .cfg_length(cfg_length),
      .noise_prob(noise_prob), .cca_thresh(cca_thresh),
      .scan_en(scan_en), .test_mode(test_mode),
      .tx_fifo_wr(tx_fifo_wr), .tx_fifo_wdata(tx_fifo_wdata), .rx_fifo_rd(rx_fifo_rd),
      .st_tx_busy(tx_busy), .st_rx_busy(ctrl_rx_en), .st_sfd_det(sfd_seen),
      .st_crc_ok(rx_crc_ok), .st_cca(1'b0),
      .st_tx_full(tx_full), .st_tx_empty(tx_empty),
      .st_rx_full(rx_full), .st_rx_empty(rx_empty),
      .tx_level(tx_level), .rx_level(rx_level), .rx_fifo_rdata(rx_head),
      .rx_signal(rx_sig), .rx_service(rx_svc), .rx_length(rx_len),
      .rssi(8'd0), .irq_set(irq_set));

  // P1 nets intentionally unused in P0
  wire _unused = &{1'b0, ctrl_mode, ctrl_noise_en, noise_prob, cca_thresh};
endmodule
`default_nettype wire
