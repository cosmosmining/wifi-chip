`default_nettype none
//============================================================================
// bl_rx - RX chain + long-PLCP parse. Oversampled chip stream ->
// correlator -> DBPSK decode -> descramble -> logical bits -> PLCP FSM:
//   SEARCH : slide a 16-bit window; match SFD 0xF3A0 (descrambler self-syncs in SYNC)
//   HEADER : collect 48 bits, CRC-16 over SIGNAL|SERVICE|LENGTH, compare to RX CRC
//   PSDU   : collect LENGTH octets, emit byte_valid/byte_data (MSB-first)
// Pure stream sink (no backpressure). Bit-accurate to model rx_dbpsk; SPEC 8/9.
//============================================================================
module bl_rx (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,       // oversampled chip valid
    input  wire        in_chip,
    output reg         sfd,            // 1-cycle pulse on SFD detect
    output reg         crc_ok,
    output reg         crc_err,        // 1-cycle pulse on bad header CRC
    output reg  [7:0]  rx_signal,
    output reg  [7:0]  rx_service,
    output reg  [15:0] rx_length,
    output reg         byte_valid,
    output reg  [7:0]  byte_data,
    output wire        corr_valid,     // 1 per symbol: correlation magnitude valid
    output wire [7:0]  corr_mag,       // |correlation peak| for CCA / RSSI (P1)
    output reg         done            // 1-cycle pulse at end of PSDU
`ifdef FORMAL
    , output wire [1:0] f_state        // formal-only FSM state observation
`endif
);
  localparam [15:0] SFD = 16'hF3A0;
  localparam [1:0]  S_SEARCH=2'd0, S_HDR=2'd1, S_PSDU=2'd2, S_DONE=2'd3;

  // --- RX datapath pipeline ---
  wire        co_v, co_sym, db_v, db_b, ds_v, ds_b;
  wire signed [7:0] co_corr;     // correlation peak (CCA/RSSI in P1)
  bl_correlator u_corr (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
      .in_chip(in_chip), .out_valid(co_v), .out_sym(co_sym), .out_corr(co_corr));
  assign corr_valid = co_v;
  assign corr_mag   = co_corr[7] ? (~co_corr + 8'd1) : co_corr;   // |correlation|
  bl_dbpsk #(.DECODE(1'b1)) u_dec (.clk(clk), .rst_n(rst_n), .clear(1'b0),
      .in_valid(co_v), .in_bit(co_sym), .out_valid(db_v), .out_bit(db_b));
  bl_scrambler #(.DESCRAMBLE(1'b1)) u_descr (.clk(clk), .rst_n(rst_n), .clear(1'b0),
      .in_valid(db_v), .in_bit(db_b), .out_valid(ds_v), .out_bit(ds_b));

  // logical bit stream
  wire lv = ds_v;
  wire lb = ds_b;

  reg  [1:0]  state;
  reg  [14:0] win;          // 15 prior bits; newwin appends the current bit
  reg  [46:0] hdrsh;        // 47 prior header bits; newhdr appends the current bit
  reg  [5:0]  hdrcnt;       // 0..47
  reg  [15:0] byte_idx;
  reg  [2:0]  bitc;
  reg  [6:0]  cur_byte;     // 7 prior payload bits; byte_data appends the 8th

  wire [15:0] crc_val;
  reg         crc_iv;
  bl_crc16 u_crc (.clk(clk), .rst_n(rst_n), .clear(state==S_SEARCH),
                  .in_valid(crc_iv), .in_bit(lb), .crc_out(crc_val));

  wire [15:0] newwin = {win, lb};
  wire [47:0] newhdr = {hdrsh, lb};

`ifdef FORMAL
  assign f_state = state;
`endif

  always @(posedge clk) begin
    if (!rst_n) begin
      state<=S_SEARCH; win<=15'd0; hdrsh<=47'd0; hdrcnt<=6'd0;
      byte_idx<=16'd0; bitc<=3'd0; cur_byte<=7'd0; crc_iv<=1'b0;
      sfd<=1'b0; crc_ok<=1'b0; crc_err<=1'b0; rx_signal<=8'd0; rx_service<=8'd0;
      rx_length<=16'd0; byte_valid<=1'b0; byte_data<=8'd0; done<=1'b0;
    end else begin
      sfd<=1'b0; byte_valid<=1'b0; done<=1'b0; crc_iv<=1'b0; crc_err<=1'b0;
      if (lv) begin
        case (state)
          S_SEARCH: begin
            win <= newwin[14:0];
            if (newwin == SFD) begin
              sfd<=1'b1; state<=S_HDR; hdrcnt<=6'd0;
            end
          end
          S_HDR: begin
            hdrsh <= newhdr[46:0];
            if (hdrcnt < 6'd32) crc_iv <= 1'b1;   // feed CRC over first 32 bits
            if (hdrcnt == 6'd47) begin
              rx_signal  <= newhdr[47:40];
              rx_service <= newhdr[39:32];
              rx_length  <= newhdr[31:16];
              crc_ok     <= (crc_val == newhdr[15:0]);
              if ((crc_val == newhdr[15:0]) && (newhdr[31:16] != 16'd0)) begin
                state<=S_PSDU; byte_idx<=16'd0; bitc<=3'd0;
              end else begin
                if (crc_val == newhdr[15:0]) done<=1'b1;  // length 0, crc ok
                else crc_err<=1'b1;                        // bad header CRC
                state<=S_SEARCH; win<=15'd0;
              end
            end else begin
              hdrcnt <= hdrcnt + 6'd1;
            end
          end
          S_PSDU: begin
            if (bitc == 3'd7) begin
              byte_valid <= 1'b1;
              byte_data  <= {cur_byte, lb};
              bitc <= 3'd0;
              if (byte_idx == rx_length - 16'd1) begin
                state<=S_DONE;
              end else begin
                byte_idx <= byte_idx + 16'd1;
              end
            end else begin
              cur_byte <= {cur_byte[5:0], lb};
              bitc <= bitc + 3'd1;
            end
          end
          default: ; // S_DONE handled below
        endcase
      end
      if (state == S_DONE) begin
        done<=1'b1; state<=S_SEARCH; win<=15'd0;
      end
    end
  end
endmodule
`default_nettype wire
