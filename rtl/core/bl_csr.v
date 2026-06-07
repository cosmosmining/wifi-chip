`default_nettype none
//============================================================================
// bl_csr - APB3 control/status registers implementing regs/barkerlink.rdl.
//
// The RDL remains the single source for the register MAP (documentation + C header
// via `make regs`); this block is the hand-written Verilog-2001 implementation of
// that map kept lockstep with it by test_csr (DECISIONS D-0109). APB3 is zero-wait
// (pready=1). Pulse outputs (tx_start, soft_rst, tx_fifo_wr, rx_fifo_rd) are 1 cycle.
//============================================================================
module bl_csr (
    input  wire        clk,
    input  wire        rst_n,
    // APB3
    input  wire        psel,
    input  wire        penable,
    input  wire        pwrite,
    input  wire [7:0]  paddr,
    input  wire [31:0] pwdata,
    output reg  [31:0] prdata,
    output wire        pready,
    output wire        irq,             // level: any enabled IRQ pending
    // control outputs (reg -> core)
    output reg         ctrl_en,
    output reg         ctrl_rx_en,
    output reg         ctrl_loopback,
    output reg         ctrl_mode,
    output reg         ctrl_noise_en,
    output reg         tx_start,        // 1-cycle pulse
    output reg         soft_rst,        // 1-cycle pulse
    output reg  [7:0]  cfg_signal,
    output reg  [7:0]  cfg_service,
    output reg  [15:0] cfg_length,
    output reg  [15:0] noise_prob,
    output reg  [7:0]  cca_thresh,
    output reg         scan_en,
    output reg         test_mode,
    output reg         tx_fifo_wr,      // 1-cycle pulse on TX_FIFO write
    output reg  [7:0]  tx_fifo_wdata,
    output reg         rx_fifo_rd,      // 1-cycle pulse on RX_FIFO read
    // status inputs (core -> reg)
    input  wire        st_tx_busy,
    input  wire        st_rx_busy,
    input  wire        st_sfd_det,
    input  wire        st_crc_ok,
    input  wire        st_cca,
    input  wire        st_tx_full,
    input  wire        st_tx_empty,
    input  wire        st_rx_full,
    input  wire        st_rx_empty,
    input  wire [4:0]  tx_level,
    input  wire [4:0]  rx_level,
    input  wire [7:0]  rx_fifo_rdata,
    input  wire [7:0]  rx_signal,
    input  wire [7:0]  rx_service,
    input  wire [15:0] rx_length,
    input  wire [7:0]  rssi,
    input  wire [5:0]  irq_set          // event pulses set IRQ_STATUS
);
  assign pready = 1'b1;
  wire wr = psel & penable & pwrite;
  wire rd = psel & penable & ~pwrite;
  wire [5:0] widx = paddr[7:2];

  reg [5:0] irq_status;
  reg [5:0] irq_en;
  wire [5:0] irq_clr = (wr && widx == 6'd4) ? pwdata[5:0] : 6'd0;
  assign irq = |(irq_status & irq_en);
  wire _unused_csr = &{1'b0, paddr[1:0]};   // word-aligned; byte offset unused

  always @(posedge clk) begin
    if (!rst_n) begin
      ctrl_en<=1'b0; ctrl_rx_en<=1'b0; ctrl_loopback<=1'b0; ctrl_mode<=1'b0;
      ctrl_noise_en<=1'b0; tx_start<=1'b0; soft_rst<=1'b0; irq_en<=6'd0;
      cfg_signal<=8'h0A; cfg_service<=8'h00; cfg_length<=16'd0;
      noise_prob<=16'd0; cca_thresh<=8'h20; scan_en<=1'b0; test_mode<=1'b0;
      tx_fifo_wr<=1'b0; tx_fifo_wdata<=8'd0; rx_fifo_rd<=1'b0; irq_status<=6'd0;
    end else begin
      tx_start<=1'b0; soft_rst<=1'b0; tx_fifo_wr<=1'b0; rx_fifo_rd<=1'b0;
      irq_status <= (irq_status & ~irq_clr) | irq_set;   // sticky set, W1C
      if (wr) begin
        case (widx)
          6'd1: begin // CTRL
            ctrl_en<=pwdata[0]; tx_start<=pwdata[1]; ctrl_rx_en<=pwdata[2];
            ctrl_loopback<=pwdata[3]; ctrl_mode<=pwdata[4]; ctrl_noise_en<=pwdata[5];
            soft_rst<=pwdata[8];
          end
          6'd3: irq_en<=pwdata[5:0];                      // IRQ_EN
          6'd5: begin tx_fifo_wr<=1'b1; tx_fifo_wdata<=pwdata[7:0]; end // TX_FIFO
          6'd8: begin cfg_signal<=pwdata[7:0]; cfg_service<=pwdata[15:8];
                      cfg_length<=pwdata[31:16]; end      // TXCFG
          6'd10: noise_prob<=pwdata[15:0];                // NOISE
          6'd11: cca_thresh<=pwdata[7:0];                 // CCA_CFG
          6'd13: begin scan_en<=pwdata[0]; test_mode<=pwdata[1]; end // TEST
          default: ;
        endcase
      end
      if (rd && widx == 6'd6) rx_fifo_rd<=1'b1;           // RX_FIFO pop on read
    end
  end

  // read mux
  always @* begin
    case (widx)
      6'd0:  prdata = {16'h424C, 8'h01, 8'h00};
      6'd1:  prdata = {23'd0, 1'b0 /*soft_rst*/, 2'd0, ctrl_noise_en, ctrl_mode,
                       ctrl_loopback, ctrl_rx_en, 1'b0 /*tx_start*/, ctrl_en};
      6'd2:  prdata = {23'd0, st_rx_empty, st_rx_full, st_tx_empty, st_tx_full,
                       st_cca, st_crc_ok, st_sfd_det, st_rx_busy, st_tx_busy};
      6'd3:  prdata = {26'd0, irq_en};
      6'd4:  prdata = {26'd0, irq_status};
      6'd6:  prdata = {24'd0, rx_fifo_rdata};
      6'd7:  prdata = {19'd0, rx_level, 3'd0, tx_level};
      6'd8:  prdata = {cfg_length, cfg_service, cfg_signal};
      6'd9:  prdata = {rx_length, rx_service, rx_signal};
      6'd10: prdata = {16'd0, noise_prob};
      6'd11: prdata = {24'd0, cca_thresh};
      6'd12: prdata = {24'd0, rssi};
      6'd13: prdata = {30'd0, test_mode, scan_en};
      default: prdata = 32'd0;
    endcase
  end
endmodule
`default_nettype wire
