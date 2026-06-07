`default_nettype none
//============================================================================
// tt_um_barkerlink - Tiny Tapeout top for the BarkerLink DSSS baseband.
//
// SPI(mode0) -> APB3 bridge -> barkerlink_core (CSR + TX/RX FIFOs + DSSS TX/RX +
// internal loopback + IRQ). Pin map per SPEC sec 3.2 (operator-approved). Scan/test
// mode on uio lands in Phase 6; uio is held as inputs for now.
//============================================================================
module tt_um_barkerlink (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
  // APB3 between the SPI bridge and the core
  wire        psel, penable, pwrite, pready;
  wire [7:0]  paddr;
  wire [31:0] pwdata, prdata;
  wire        miso, irq, cca, scan_en, test_mode, sfd_det, crc_ok;
  wire        tx_chip, tx_chip_valid;

  bl_spi_apb u_spi (
      .clk(clk), .rst_n(rst_n),
      .sclk(ui_in[0]), .csn(ui_in[1]), .mosi(ui_in[2]), .miso(miso),
      .psel(psel), .penable(penable), .pwrite(pwrite), .paddr(paddr),
      .pwdata(pwdata), .prdata(prdata), .pready(pready));

  barkerlink_core u_core (
      .clk(clk), .rst_n(rst_n),
      .psel(psel), .penable(penable), .pwrite(pwrite), .paddr(paddr),
      .pwdata(pwdata), .prdata(prdata), .pready(pready),
      .tx_chip(tx_chip), .tx_chip_valid(tx_chip_valid),
      .rx_chip_ext(ui_in[3]), .rx_chip_valid_ext(ui_in[4]),
      .irq(irq), .cca(cca), .scan_en(scan_en), .test_mode(test_mode),
      .sfd_det(sfd_det), .crc_ok(crc_ok));

  // uo_out: [0]MISO [1]IRQ [2]TXchip [3]TXchip_valid [4]CCA [5]- [6]SFD_DET [7]CRC_OK
  assign uo_out = {crc_ok, sfd_det, 1'b0, cca, tx_chip_valid, tx_chip, irq, miso};

  // uio reserved as inputs until scan/test (Phase 6)
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // intentionally unused in P0 (ena, reserved ui, uio inputs, scan/test sidebands)
  wire _unused = &{ena, ui_in[7:5], uio_in, scan_en, test_mode, 1'b0};
endmodule
`default_nettype wire
