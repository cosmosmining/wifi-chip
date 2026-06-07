`default_nettype none
//============================================================================
// bl_spi_apb - SPI slave (mode 0, MSB-first) -> APB3 master bridge.
//
// Oversampled in the clk domain (2-FF synchronizers on sclk/csn/mosi, edge detect)
// so there is no second clock domain (D-0110). Transaction framed by CSn: 1 command
// byte {wr, addr[6:0]} + 4 data bytes (32-bit, big-endian). On a read the command
// triggers an APB read and the 32-bit result is shifted out on MISO. APB is zero-wait.
//============================================================================
module bl_spi_apb (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        sclk,
    input  wire        csn,
    input  wire        mosi,
    output reg         miso,
    output reg         psel,
    output reg         penable,
    output reg         pwrite,
    output reg  [7:0]  paddr,
    output reg  [31:0] pwdata,
    input  wire [31:0] prdata,
    input  wire        pready
);
  // --- synchronize async SPI inputs into clk domain ---
  reg [1:0] sclk_q, csn_q, mosi_q;
  always @(posedge clk) begin
    if (!rst_n) begin sclk_q<=2'b0; csn_q<=2'b11; mosi_q<=2'b0; end
    else begin
      sclk_q<={sclk_q[0],sclk}; csn_q<={csn_q[0],csn}; mosi_q<={mosi_q[0],mosi};
    end
  end
  wire sclk_s = sclk_q[1], csn_s = csn_q[1], mosi_s = mosi_q[1];
  reg sclk_d;
  always @(posedge clk) sclk_d <= (!rst_n) ? 1'b0 : sclk_s;
  wire sclk_re = sclk_s & ~sclk_d;
  wire sclk_fe = ~sclk_s & sclk_d;

  reg  [30:0] in_sh;
  reg  [31:0] out_sh;
  reg  [5:0]  bitcnt;
  reg         cmd_write;
  reg  [7:0]  cmd_addr;
  wire [7:0]  cmd_now  = {in_sh[6:0],  mosi_s};
  wire [31:0] data_now = {in_sh[30:0], mosi_s};

  localparam [1:0] A_IDLE=2'd0, A_SETUP=2'd1, A_ACCESS=2'd2;
  reg [1:0]  astate;
  reg        trig_rd, trig_wr;
  reg [7:0]  req_addr;
  reg [31:0] req_wdata;

  always @(posedge clk) begin
    if (!rst_n) begin
      in_sh<=31'd0; out_sh<=32'd0; bitcnt<=6'd0; cmd_write<=1'b0; cmd_addr<=8'd0;
      miso<=1'b0; psel<=1'b0; penable<=1'b0; pwrite<=1'b0; paddr<=8'd0; pwdata<=32'd0;
      astate<=A_IDLE; trig_rd<=1'b0; trig_wr<=1'b0; req_addr<=8'd0; req_wdata<=32'd0;
    end else begin
      trig_rd<=1'b0; trig_wr<=1'b0;
      if (csn_s) begin
        bitcnt <= 6'd0;
      end else begin
        if (sclk_re) begin
          in_sh  <= {in_sh[29:0], mosi_s};
          bitcnt <= bitcnt + 6'd1;
          if (bitcnt == 6'd7) begin
            cmd_write <= cmd_now[7];
            cmd_addr  <= {cmd_now[5:0], 2'b00};
            if (!cmd_now[7]) begin trig_rd<=1'b1; req_addr<={cmd_now[5:0],2'b00}; end
          end
          if (bitcnt == 6'd39 && cmd_write) begin
            trig_wr<=1'b1; req_addr<=cmd_addr; req_wdata<=data_now;
          end
        end
        if (sclk_fe) begin
          miso   <= out_sh[31];
          out_sh <= {out_sh[30:0], 1'b0};
        end
      end
      case (astate)
        A_IDLE: begin
          psel<=1'b0; penable<=1'b0;
          if (trig_rd) begin psel<=1'b1; pwrite<=1'b0; paddr<=req_addr; astate<=A_SETUP; end
          else if (trig_wr) begin
            psel<=1'b1; pwrite<=1'b1; paddr<=req_addr; pwdata<=req_wdata; astate<=A_SETUP;
          end
        end
        A_SETUP: begin penable<=1'b1; astate<=A_ACCESS; end
        A_ACCESS: if (pready) begin
                    if (!pwrite) out_sh<=prdata;
                    psel<=1'b0; penable<=1'b0; astate<=A_IDLE;
                  end
        default: astate<=A_IDLE;
      endcase
    end
  end

  wire _unused = &{1'b0, cmd_now[6]};   // word addr uses cmd[5:0]; cmd[6] reserved
endmodule
`default_nettype wire
