// SPDX-License-Identifier: Apache-2.0
// Smoke test for rtl/wrapper/fft256_stream.sv. A bare fft256 free-runs on the
// same input sequence as the reference; the wrapper, driven with random
// in_valid / out_ready stalls, must present exactly the reference sample for
// each step, with the frame markers in the right places. Structural check
// only: the bit-exact model bench is a separate item.
module tb_fft256_stream;
  reg clk = 0;
  always #5 clk = ~clk;
  reg rst = 1;

  // input sample sequence as a function of the sample index
  function automatic [15:0] smp_re(input integer i);
    smp_re = (i * 1237 + (i >> 3) * 91 + 17) & 16'h0FFF;
  endfunction
  function automatic [15:0] smp_im(input integer i);
    smp_im = (i * 733 + (i >> 2) * 411 + 5) & 16'h07FF;
  endfunction

  // reference core, always enabled
  integer ref_t = 0;
  wire signed [15:0] r_re, r_im;
  wire r_v;
  reg signed [15:0] ri_re, ri_im;
  fft256 u_ref (.clk(clk), .rst(rst), .en(1'b1), .in_re(ri_re), .in_im(ri_im),
                .out_re(r_re), .out_im(r_im), .out_valid(r_v));
  reg signed [15:0] ref_re [0:4095];
  reg signed [15:0] ref_im [0:4095];
  reg               ref_cv [0:4095];

  // device under test
  reg d_valid = 0, d_oready = 0;
  reg signed [15:0] di_re, di_im;
  wire d_iready, d_ovalid, d_first, d_last;
  wire signed [15:0] d_re, d_im;
  fft256_stream u_dut (.clk(clk), .rst(rst), .in_valid(d_valid), .in_ready(d_iready),
                       .in_re(di_re), .in_im(di_im), .out_valid(d_ovalid),
                       .out_ready(d_oready), .out_re(d_re), .out_im(d_im),
                       .out_first(d_first), .out_last(d_last));

  integer dut_t, t0, errors = 0, checked = 0, stalls = 0, seed = 1;
  integer k, run, nclk;
  reg exp_cv;
  reg signed [15:0] cmp_re;

  task automatic fail(input [255:0] what);
    begin errors = errors + 1; $display("MISMATCH %0s at step %0d", what, dut_t); end
  endtask

  task automatic do_run(input integer nclocks, input integer pstall);
    begin
      rst = 1; ref_t = 0; dut_t = 0; t0 = -1;
      repeat (3) @(posedge clk);
      #1 rst = 0;
      for (nclk = 0; nclk < nclocks; nclk = nclk + 1) begin
        @(negedge clk);
        ri_re = smp_re(ref_t); ri_im = smp_im(ref_t);
        di_re = smp_re(dut_t); di_im = smp_im(dut_t);
        d_valid  = ($random(seed) & 255) >= pstall;
        d_oready = ($random(seed) & 255) >= pstall;
        #1;
        ref_re[ref_t] = r_re; ref_im[ref_t] = r_im; ref_cv[ref_t] = r_v;
        if (r_v && t0 < 0) t0 = ref_t;
        exp_cv = ref_cv[dut_t];
        if (d_iready !== (d_oready | ~exp_cv)) fail("in_ready");
        if (d_ovalid !== (exp_cv & d_valid)) fail("out_valid");
        if (d_ovalid) begin
          cmp_re = d_re;
`ifdef NEGCTL
          if (dut_t == 600) cmp_re = d_re ^ 16'h0010;
`endif
          if (cmp_re !== ref_re[dut_t] || d_im !== ref_im[dut_t]) fail("data");
          if (d_first !== (((dut_t - t0) % 256) == 0)) fail("out_first");
          if (d_last  !== (((dut_t - t0) % 256) == 255)) fail("out_last");
          if (d_oready) checked = checked + 1;
        end else if (d_first || d_last) fail("marker without valid");
        if (d_valid && !d_iready) stalls = stalls + 1;
        if (d_valid && d_iready) dut_t = dut_t + 1;
        @(posedge clk);
        ref_t = ref_t + 1;
      end
    end
  endtask

  initial begin
    ri_re = 0; ri_im = 0; di_re = 0; di_im = 0;
    // run 1: stop mid-frame, then run 2 restarts from reset (reset during a frame)
    do_run(700, 90);
    do_run(2200, 100);
    do_run(1800, 0);   // no stalls: back-to-back frames
    $display("checked=%0d stalls=%0d errors=%0d", checked, stalls, errors);
    if (checked < 768 || stalls < 50) begin errors = errors + 1; $display("vacuous run"); end
    if (errors == 0) $display("PASS fft256_stream smoke");
    else $display("FAIL fft256_stream smoke: %0d errors", errors);
    $finish;
  end
endmodule
