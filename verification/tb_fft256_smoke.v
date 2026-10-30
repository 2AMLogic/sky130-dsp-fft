// Streaming testbench for the generated fft256 (verification/test_fft256_smoke.py).
// Feeds NSAMP stimulus words (packed {re,im}, 16 bits each) back to back, then zeros
// until NSAMP output samples were captured from the first cycle out_valid is high.
// +perturb=<i> flips the LSB of out_re on captured sample i (negative control only).
`timescale 1ns/1ps
module tb_fft256_smoke;
  parameter NSAMP = 256;
  reg clk = 0;
  reg rst = 1;
  reg en = 0;
  reg signed [15:0] in_re = 0, in_im = 0;
  wire signed [15:0] out_re, out_im;
  wire out_valid;
  reg [31:0] stim [0:NSAMP-1];
  integer i, ncap, fd, perturb, first_valid, cyc;
  reg [15:0] cre;

  fft256 dut (.clk(clk), .rst(rst), .en(en), .in_re(in_re), .in_im(in_im),
              .out_re(out_re), .out_im(out_im), .out_valid(out_valid));
  always #5 clk = ~clk;

  initial begin
    if (!$value$plusargs("perturb=%d", perturb)) perturb = -1;
    $readmemh("stim.hex", stim);
    fd = $fopen("out.hex", "w");
    ncap = 0; first_valid = -1; cyc = 0;
    repeat (3) @(negedge clk);
    rst = 0; en = 1;
    while (ncap < NSAMP && cyc < NSAMP + 4096) begin
      // Inputs change on the falling edge; outputs are sampled on the same edge.
      if (cyc < NSAMP) begin
        in_re = stim[cyc][31:16];
        in_im = stim[cyc][15:0];
      end else begin
        in_re = 0;
        in_im = 0;
      end
      if (out_valid) begin
        if (first_valid < 0) first_valid = cyc;
        cre = out_re;
        if (ncap == perturb) cre = cre ^ 16'h0001;
        $fdisplay(fd, "%04x%04x", cre, out_im);
        ncap = ncap + 1;
      end
      cyc = cyc + 1;
      @(negedge clk);
    end
    $fclose(fd);
    $display("captured=%0d first_valid_cycle=%0d", ncap, first_valid);
    $finish;
  end
endmodule
