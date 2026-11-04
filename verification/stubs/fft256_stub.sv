// SPDX-License-Identifier: Apache-2.0
// Port-only stand-in for the generated fft256 so `make lint-wrapper` lints the
// hand-written wrapper alone (the generated tree is not ours to lint-fix). The
// wrapper smoke test elaborates the real core, so a port drift fails there.
module fft256 (
    input  logic               clk,
    input  logic               rst,
    input  logic               en,
    input  logic signed [15:0] in_re,
    input  logic signed [15:0] in_im,
    output logic signed [15:0] out_re,
    output logic signed [15:0] out_im,
    output logic               out_valid
);
  logic unused;
  assign unused = &{clk, rst, en, in_re, in_im};
  assign out_re = 16'sd0;
  assign out_im = 16'sd0;
  assign out_valid = 1'b0;
endmodule
