`default_nettype none
//============================================================================
// bl_tx - long-PLCP TX: assembles SYNC|SFD|header|PSDU logical bits, runs them
// through the (separately lockstep-verified) scrambler -> DBPSK -> Barker spreader
// pipeline, and emits the 4x-oversampled 1-bit chip stream.
//
// One logical bit is injected at a time and the FSM waits for its 44-chip symbol to
// finish spreading (saw_busy/ready handshake) before injecting the next, so the
// single-pulse valid ripples through the pipeline in order. Header CRC-16 is computed
// inline over SIGNAL|SERVICE|LENGTH. PSDU bytes are pulled from a FIFO (psdu_data = head,
// psdu_pop advances to the next byte). Bit order/seed per SPEC sec 6/7/9.
//============================================================================
module bl_tx #(
    parameter [7:0] SYNC_LEN = 8'd128   // preamble ones; taped-out value 128
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,          // pulse to begin a frame
    input  wire [7:0]  signal,
    input  wire [7:0]  service,
    input  wire [15:0] length,         // PSDU octets
    input  wire [7:0]  psdu_data,      // current TX FIFO head byte
    output reg         psdu_pop,       // 1-cycle pulse: advance FIFO to next byte
    output reg         busy,
    output reg         done,           // 1-cycle pulse at end of frame
    output wire        chip_valid,
    output wire        chip_out
);
  localparam [2:0] F_IDLE=3'd0, F_SYNC=3'd1, F_SFD=3'd2, F_HDR=3'd3,
                   F_CRC=3'd4, F_PSDU=3'd5, F_DONE=3'd6;
  localparam [15:0] SFD = 16'hF3A0;

  reg  [2:0]  field;
  reg  [7:0]  cnt;         // bit index within SYNC/SFD/HDR/CRC
  reg  [2:0]  bit_in_byte;
  reg  [15:0] pbyte;       // PSDU byte index
  reg  [7:0]  tx_byte;     // latched current PSDU byte (avoids FIFO-head race)
  reg         inj_busy, saw_busy;

  // --- pipeline submodule wires ---
  reg         sc_iv, sc_ib, crc_iv;
  wire        sc_ov, sc_ob, db_ov, db_ob, sp_ready, sp_ov, sp_oc;
  wire [15:0] crc_val;

  // --- current logical bit by field ---
  wire [31:0] hdr_word = {signal, service, length};
  reg  lbit;
  always @* begin
    case (field)
      F_SYNC: lbit = 1'b1;
      F_SFD:  lbit = SFD[15 - cnt[3:0]];
      F_HDR:  lbit = hdr_word[31 - cnt[4:0]];
      F_CRC:  lbit = crc_val[15 - cnt[3:0]];
      F_PSDU: lbit = tx_byte[7 - bit_in_byte];
      default: lbit = 1'b0;
    endcase
  end

  wire bit_done = inj_busy && sp_ready && saw_busy;

  always @(posedge clk) begin
    if (!rst_n) begin
      field<=F_IDLE; cnt<=8'd0; bit_in_byte<=3'd0; pbyte<=16'd0; tx_byte<=8'd0;
      inj_busy<=1'b0; saw_busy<=1'b0; busy<=1'b0; done<=1'b0; psdu_pop<=1'b0;
      sc_iv<=1'b0; sc_ib<=1'b0; crc_iv<=1'b0;
    end else begin
      sc_iv<=1'b0; crc_iv<=1'b0; done<=1'b0; psdu_pop<=1'b0;
      case (field)
        F_IDLE: begin
          busy<=1'b0;
          if (start) begin
            field<=F_SYNC; cnt<=8'd0; bit_in_byte<=3'd0;
            pbyte<=16'd0; inj_busy<=1'b0; saw_busy<=1'b0; busy<=1'b1;
          end
        end
        F_DONE: begin done<=1'b1; busy<=1'b0; field<=F_IDLE; end
        default: begin // any active field
          if (!inj_busy) begin
            sc_iv<=1'b1; sc_ib<=lbit;
            if (field==F_HDR) begin crc_iv<=1'b1; end
            inj_busy<=1'b1; saw_busy<=1'b0;
          end else begin
            if (!sp_ready) saw_busy<=1'b1;
            if (bit_done) begin
              inj_busy<=1'b0;
              case (field)
                F_SYNC: if (cnt==SYNC_LEN-8'd1) begin field<=F_SFD; cnt<=8'd0; end
                        else cnt<=cnt+8'd1;
                F_SFD:  if (cnt==8'd15)  begin field<=F_HDR; cnt<=8'd0; end
                        else cnt<=cnt+8'd1;
                F_HDR:  if (cnt==8'd31)  begin field<=F_CRC; cnt<=8'd0; end
                        else cnt<=cnt+8'd1;
                F_CRC:  if (cnt==8'd15) begin
                          if (length==16'd0) begin
                            field<=F_DONE;
                          end else begin
                            // latch byte 0 and advance FIFO head for byte 1
                            field<=F_PSDU; bit_in_byte<=3'd0; pbyte<=16'd0;
                            tx_byte<=psdu_data; psdu_pop<=1'b1;
                          end
                        end else cnt<=cnt+8'd1;
                F_PSDU: if (bit_in_byte==3'd7) begin
                          if (pbyte==length-16'd1) begin
                            field<=F_DONE;
                          end else begin
                            // latch next byte (head settled) and advance FIFO
                            bit_in_byte<=3'd0; pbyte<=pbyte+16'd1;
                            tx_byte<=psdu_data; psdu_pop<=1'b1;
                          end
                        end else bit_in_byte<=bit_in_byte+3'd1;
                default: ;
              endcase
            end
          end
        end
      endcase
    end
  end

  // CRC seeded (clear) during SFD so it is 0xFFFF at HDR start, then HOLDS through
  // F_CRC so crc_val is stable while the 16 CRC bits are emitted.
  bl_crc16 u_crc (.clk(clk), .rst_n(rst_n), .clear(field==F_SFD),
                  .in_valid(crc_iv), .in_bit(sc_ib), .crc_out(crc_val));

  bl_scrambler #(.DESCRAMBLE(1'b0)) u_scr (
      .clk(clk), .rst_n(rst_n), .clear(start),
      .in_valid(sc_iv), .in_bit(sc_ib), .out_valid(sc_ov), .out_bit(sc_ob));

  bl_dbpsk #(.DECODE(1'b0)) u_dbpsk (
      .clk(clk), .rst_n(rst_n), .clear(start),
      .in_valid(sc_ov), .in_bit(sc_ob), .out_valid(db_ov), .out_bit(db_ob));

  bl_spreader u_spread (
      .clk(clk), .rst_n(rst_n), .in_valid(db_ov), .in_sym(db_ob),
      .ready(sp_ready), .out_valid(sp_ov), .out_chip(sp_oc));

  assign chip_valid = sp_ov;
  assign chip_out   = sp_oc;
endmodule
`default_nettype wire
