// SPDX-License-Identifier: Apache-2.0
// Hand-written valid/ready streaming wrapper around the generated fft256 core
// (rtl/generated/fft256.v). Not generated; do not place it under rtl/generated.
//
// The core is a lock-step single-path-delay-feedback pipeline: every enabled
// clock consumes one input sample and, once the pipeline has filled, presents
// one output sample. This wrapper therefore ties the core's `en` stall port to
// the handshakes:
//   * in_ready  = out_ready | ~core_valid   (stall only once outputs are live)
//   * en        = in_valid & in_ready       (one input accepted == one step)
//   * out_valid = core_valid & in_valid     (an output moves with an input)
// so a transfer on the input side and, after the fill, on the output side are
// the same event and no sample is dropped or duplicated.
//
// Framing: input frames are delimited by sample count from reset (256 samples
// per frame, no input markers). out_first / out_last mark sample 0 / 255 of each
// output frame. There is no flush: the last frame's tail leaves the pipeline
// only while further input (the next frame or zero padding) is accepted.
// `rst` is synchronous, active high, and clears the core and the frame counter.
module fft256_stream (
    input  logic               clk,
    input  logic               rst,
    input  logic               in_valid,
    output logic               in_ready,
    input  logic signed [15:0] in_re,
    input  logic signed [15:0] in_im,
    output logic               out_valid,
    input  logic               out_ready,
    output logic signed [15:0] out_re,
    output logic signed [15:0] out_im,
    output logic               out_first,
    output logic               out_last
);
  logic       core_valid;
  logic       en;
  logic [7:0] ocnt;  // output sample index within the frame

  assign in_ready  = out_ready | ~core_valid;
  assign en        = in_valid & in_ready;
  assign out_valid = core_valid & in_valid;

  always_ff @(posedge clk) begin
    if (rst) ocnt <= 8'd0;
    else if (en & core_valid) ocnt <= ocnt + 8'd1;
  end

  assign out_first = out_valid & (ocnt == 8'd0);
  assign out_last  = out_valid & (ocnt == 8'hFF);

  fft256 u_core (
      .clk(clk), .rst(rst), .en(en),
      .in_re(in_re), .in_im(in_im),
      .out_re(out_re), .out_im(out_im), .out_valid(core_valid)
  );
endmodule
