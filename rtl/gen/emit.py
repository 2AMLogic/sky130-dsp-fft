# SPDX-License-Identifier: Apache-2.0
"""Verilog emitter for the radix-2^2 SDF FFT. Pure function of the params."""
import math
import os

SPDX = "// SPDX-License-Identifier: Apache-2.0\n"

_RND = """\
module fft_rnd #(parameter W = 8, parameter S = 0, parameter CONV = 1) (
    input  signed [W-1:0]   x,
    output signed [W-S-1:0] y
);
  generate
    if (S == 0) begin : g_pass
      assign y = x;
    end else if (CONV == 0) begin : g_trunc
      wire signed [W-1:0] sh = x >>> S;
      assign y = sh[W-S-1:0];
    end else begin : g_conv
      wire [S-1:0] frac = x[S-1:0];
      wire [W-S-1:0] tr = x[W-1:S];
      wire up;
      if (S == 1) begin : g_s1
        assign up = frac[0] & tr[0];
      end else begin : g_sn
        assign up = frac[S-1] & ((|frac[S-2:0]) | tr[0]);
      end
      assign y = tr + up;
    end
  endgenerate
endmodule
"""

_STAGE = """\
module fft_sdf_stage #(
    parameter WI = 16, parameter W = 17, parameter D = 128,
    parameter ROT = 0, parameter PIPE = 0
) (
    input clk, input en, input phase, input half,
    input  signed [WI-1:0] in_re, input signed [WI-1:0] in_im,
    output signed [W-1:0]  out_re, output signed [W-1:0] out_im
);
  wire signed [W-1:0] xr = in_re;
  wire signed [W-1:0] xi = in_im;
  wire do_rot = (ROT != 0) & phase & half;
  wire signed [W-1:0] ur = do_rot ? xi : xr;
  wire signed [W-1:0] ui = do_rot ? -xr : xi;

  reg [D*W-1:0] sr_re;
  reg [D*W-1:0] sr_im;
  wire signed [W-1:0] yr = sr_re[D*W-1 -: W];
  wire signed [W-1:0] yi = sr_im[D*W-1 -: W];

  wire signed [W-1:0] fr = phase ? (yr - ur) : ur;
  wire signed [W-1:0] fi = phase ? (yi - ui) : ui;
  wire signed [W-1:0] br = phase ? (yr + ur) : yr;
  wire signed [W-1:0] bi = phase ? (yi + ui) : yi;

  generate
    if (D == 1) begin : g_d1
      always @(posedge clk) if (en) begin
        sr_re <= fr;
        sr_im <= fi;
      end
    end else begin : g_dn
      always @(posedge clk) if (en) begin
        sr_re <= {sr_re[(D-1)*W-1:0], fr};
        sr_im <= {sr_im[(D-1)*W-1:0], fi};
      end
    end
  endgenerate

  reg signed [W-1:0] o_re;
  reg signed [W-1:0] o_im;
  always @(posedge clk) if (en) begin
    o_re <= br;
    o_im <= bi;
  end
  assign out_re = (PIPE != 0) ? o_re : br;
  assign out_im = (PIPE != 0) ? o_im : bi;
endmodule
"""

_STAGE_RED = """\
module fft_sdf_stage #(
    parameter WI = 16, parameter W = 17, parameter D = 128,
    parameter ROT = 0, parameter PIPE = 0
) (
    input clk, input en, input phase, input half,
    input  signed [WI-1:0] in_re, input signed [WI-1:0] in_im,
    output signed [W-1:0]  out_re, output signed [W-1:0] out_im
);
  // Mid-pipeline width reduction (model _reduce, issue #162): the butterfly
  // runs one growth bit wider than the input and each emitted sum or
  // difference is rounded convergent by DRP = max(0, WI+1-W) down to W, so
  // a result wider than W is rounded, never wrapped. A caller passing
  // W >= WI+1 gets DRP = 0 and the plain width-W butterfly; a stage B
  // feeding a twiddle multiplier passes W = WI+1 and stays wide, because
  // its single rounding is the combined one inside fft_cmul.
  localparam WW = (WI + 1 > W) ? WI + 1 : W;
  localparam DRP = (WI + 1 > W) ? WI + 1 - W : 0;
  wire signed [WW-1:0] xr = in_re;
  wire signed [WW-1:0] xi = in_im;
  wire do_rot = (ROT != 0) & phase & half;
  wire signed [WW-1:0] ur = do_rot ? xi : xr;
  wire signed [WW-1:0] ui = do_rot ? -xr : xi;

  reg [D*W-1:0] sr_re;
  reg [D*W-1:0] sr_im;
  wire signed [W-1:0] yr = sr_re[D*W-1 -: W];
  wire signed [W-1:0] yi = sr_im[D*W-1 -: W];
  wire signed [WW-1:0] vr = yr;
  wire signed [WW-1:0] vi = yi;

  wire signed [WW-1:0] ar = vr - ur;
  wire signed [WW-1:0] ai = vi - ui;
  wire signed [WW-1:0] br = vr + ur;
  wire signed [WW-1:0] bi = vi + ui;

  wire signed [W-1:0] fr;
  wire signed [W-1:0] fi;
  wire signed [W-1:0] qr;
  wire signed [W-1:0] qi;
  generate
    if (DRP == 0) begin : g_keep
      assign fr = phase ? ar : ur;
      assign fi = phase ? ai : ui;
      assign qr = phase ? br : yr;
      assign qi = phase ? bi : yi;
    end else begin : g_red
      wire signed [W-1:0] ndr;
      wire signed [W-1:0] ndi;
      wire signed [W-1:0] nsr;
      wire signed [W-1:0] nsi;
      fft_rnd #(.W(WW), .S(DRP), .CONV(1)) u_dr (.x(ar), .y(ndr));
      fft_rnd #(.W(WW), .S(DRP), .CONV(1)) u_di (.x(ai), .y(ndi));
      fft_rnd #(.W(WW), .S(DRP), .CONV(1)) u_sr (.x(br), .y(nsr));
      fft_rnd #(.W(WW), .S(DRP), .CONV(1)) u_si (.x(bi), .y(nsi));
      assign fr = phase ? ndr : ur[W-1:0];
      assign fi = phase ? ndi : ui[W-1:0];
      assign qr = phase ? nsr : yr;
      assign qi = phase ? nsi : yi;
    end
  endgenerate

  generate
    if (D == 1) begin : g_d1
      always @(posedge clk) if (en) begin
        sr_re <= fr;
        sr_im <= fi;
      end
    end else begin : g_dn
      always @(posedge clk) if (en) begin
        sr_re <= {sr_re[(D-1)*W-1:0], fr};
        sr_im <= {sr_im[(D-1)*W-1:0], fi};
      end
    end
  endgenerate

  reg signed [W-1:0] o_re;
  reg signed [W-1:0] o_im;
  always @(posedge clk) if (en) begin
    o_re <= qr;
    o_im <= qi;
  end
  assign out_re = (PIPE != 0) ? o_re : qr;
  assign out_im = (PIPE != 0) ? o_im : qi;
endmodule
"""

# The arithmetic core shared verbatim by both complex-multiplier templates
# (issue #197): the three-product and four-product schedules feeding both
# accumulators into the rounders. The templates differ only around it --
# ports, widths, the shift S and the output registers -- so an arithmetic
# fix lands here once for every schedule.
_CMUL_CORE = """\
  wire signed [PW-1:0] acc_re;
  wire signed [PW-1:0] acc_im;
  generate
    if (MULT3 != 0) begin : g_m3
      wire signed [W:0]  sa = a_re + a_im;
      wire signed [TW:0] dw = w_im - w_re;
      wire signed [TW:0] sw = w_re + w_im;
      wire signed [PW-1:0] k1 = w_re * sa;
      wire signed [PW-1:0] k2 = a_re * dw;
      wire signed [PW-1:0] k3 = a_im * sw;
      assign acc_re = k1 - k3;
      assign acc_im = k1 + k2;
    end else begin : g_m4
      wire signed [PW-1:0] m1 = a_re * w_re;
      wire signed [PW-1:0] m2 = a_im * w_im;
      wire signed [PW-1:0] m3 = a_re * w_im;
      wire signed [PW-1:0] m4 = a_im * w_re;
      assign acc_re = m1 - m2;
      assign acc_im = m3 + m4;
    end
  endgenerate
  wire signed [PW-S-1:0] r_re;
  wire signed [PW-S-1:0] r_im;
  fft_rnd #(.W(PW), .S(S), .CONV(1)) u_rr (.x(acc_re), .y(r_re));
  fft_rnd #(.W(PW), .S(S), .CONV(1)) u_ri (.x(acc_im), .y(r_im));
"""

_CMUL = """\
// Twiddles are signed TW-bit fixed point with TW-2 fractional bits.
module fft_cmul #(
    parameter W = 18, parameter TW = 16, parameter MULT3 = 0, parameter PIPE = 0
) (
    input clk, input en,
    input  signed [W-1:0]  a_re, input signed [W-1:0] a_im,
    input  signed [TW-1:0] w_re, input signed [TW-1:0] w_im,
    output signed [W-1:0]  p_re, output signed [W-1:0] p_im
);
  localparam PW = W + TW + 2;
  localparam S = TW - 2;
""" + _CMUL_CORE + """\
  reg signed [W-1:0] o_re;
  reg signed [W-1:0] o_im;
  always @(posedge clk) if (en) begin
    o_re <= r_re[W-1:0];
    o_im <= r_im[W-1:0];
  end
  assign p_re = (PIPE != 0) ? o_re : r_re[W-1:0];
  assign p_im = (PIPE != 0) ? o_im : r_im[W-1:0];
endmodule
"""

_CMUL_RED = """\
// Twiddles are signed TW-bit fixed point with TW-2 fractional bits.
// Mid-pipeline width reduction (model _reduce, issue #162): the butterfly
// result arrives W = WI+1 bits wide (the fft_sdf_stage wide pass-through)
// and this multiplier performs the single combined rounding -- convergent
// by S = TW-2 + W-OW, the twiddle fraction plus the stage drop -- straight
// down to the reduced width OW. Rounding the operand down to OW before the
// multiply and the product by TW-2 after would round twice and diverge
// from the model on ties.
module fft_cmul #(
    parameter W = 19, parameter OW = 18, parameter TW = 16, parameter MULT3 = 0, parameter PIPE = 0
) (
    input clk, input en,
    input  signed [W-1:0]  a_re, input signed [W-1:0] a_im,
    input  signed [TW-1:0] w_re, input signed [TW-1:0] w_im,
    output signed [OW-1:0] p_re, output signed [OW-1:0] p_im
);
  localparam PW = W + TW + 2;
  localparam S = TW - 2 + W - OW;
""" + _CMUL_CORE + """\
  reg signed [OW-1:0] o_re;
  reg signed [OW-1:0] o_im;
  always @(posedge clk) if (en) begin
    o_re <= r_re[OW-1:0];
    o_im <= r_im[OW-1:0];
  end
  assign p_re = (PIPE != 0) ? o_re : r_re[OW-1:0];
  assign p_im = (PIPE != 0) ? o_im : r_im[OW-1:0];
endmodule
"""

_REORDER = """\
// Ping-pong reorder buffer: bit-reversed write order, natural read order.
// cw[NB] selects the write bank; the other bank is read.
module fft_reorder #(parameter NB = 8, parameter W = 16) (
    input clk, input en,
    input  [NB:0] cw,
    input  signed [W-1:0] din_re, input signed [W-1:0] din_im,
    output signed [W-1:0] dout_re, output signed [W-1:0] dout_im
);
  reg [2*W-1:0] mem [0:(2<<NB)-1];
  wire [NB-1:0] br;
  genvar g;
  generate
    for (g = 0; g < NB; g = g + 1) begin : g_br
      assign br[g] = cw[NB-1-g];
    end
  endgenerate
  always @(posedge clk) if (en) mem[cw] <= {din_im, din_re};
  wire [2*W-1:0] rd = mem[{~cw[NB], br}];
  assign dout_re = rd[W-1:0];
  assign dout_im = rd[2*W-1:W];
endmodule
"""


def _header(p):
    return (SPDX + "// Generated by rtl/gen from a parameter file with sha256 "
            + p["_sha256"] + "; do not edit.\n")


def _twrom(p, nb):
    n, tw = p["size"], p["twiddle_width"]
    scale = 1 << (tw - 2)
    lines = [
        "// Combinational twiddle table with eighth-circle symmetry; W^addr =",
        "// cos(2*pi*addr/%d) - j*sin(2*pi*addr/%d), values in Q2.%d." % (n, n, tw - 2),
        "module fft_twrom (",
        "    input  [%d:0] addr," % (nb - 1),
        "    output signed [%d:0] w_re," % (tw - 1),
        "    output signed [%d:0] w_im" % (tw - 1),
        ");",
        "  wire [1:0] quad = addr[%d:%d];" % (nb - 1, nb - 2),
        "  wire [%d:0] r = addr[%d:0];" % (nb - 3, nb - 3),
        "  wire swap = r > %d;" % (n // 8),
        "  wire [%d:0] rp = swap ? (%d - {1'b0, r}) : {1'b0, r};" % (nb - 2, n // 4),
        "  reg signed [%d:0] oc;" % (tw - 1),
        "  reg signed [%d:0] os;" % (tw - 1),
        "  always @* begin",
        "    case (rp)",
    ]
    for r in range(n // 8 + 1):
        a = 2 * math.pi * r / n
        lines.append("      %d'd%d: begin oc = %d'sd%d; os = %d'sd%d; end" % (
            nb - 1, r, tw, round(math.cos(a) * scale), tw, round(math.sin(a) * scale)))
    lines += [
        "      default: begin oc = %d'sd0; os = %d'sd0; end" % (tw, tw),
        "    endcase",
        "  end",
        "  wire signed [%d:0] cr = swap ? os : oc;" % (tw - 1),
        "  wire signed [%d:0] sr = swap ? oc : os;" % (tw - 1),
        "  reg signed [%d:0] c;" % (tw - 1),
        "  reg signed [%d:0] s;" % (tw - 1),
        "  always @* begin",
        "    case (quad)",
        "      2'd0: begin c = cr;  s = sr;  end",
        "      2'd1: begin c = -sr; s = cr;  end",
        "      2'd2: begin c = -cr; s = -sr; end",
        "      default: begin c = sr; s = -cr; end",
        "    endcase",
        "  end",
        "  assign w_re = c;",
        "  assign w_im = -s;",
        "endmodule",
    ]
    return "\n".join(lines) + "\n"


def _stage_drops(p):
    """Per radix-2 stage: (out_width, drop, has_multiplier), following the
    model's _reduce -- drop = max(0, prev+1-w), starting from input_width;
    a multiplier follows every stage B except the last (which has none)."""
    sw = p["stage_widths"]
    out = []
    prev = p["input_width"]
    for i, w in enumerate(sw):
        mul = i % 2 == 1 and i < len(sw) - 1
        out.append((w, prev + 1 - w, mul))
        prev = w
    return out


def _reduction_kinds(p):
    """(stage_reduces, cmul_widens) for the parameter set: whether any stage
    rounds a drop inside fft_sdf_stage, and whether any twiddle multiplier
    absorbs a drop (so the shared fft_cmul text is the wide template and
    every multiplier instance must pass .OW)."""
    stage_red = wide = False
    for w, drop, mul in _stage_drops(p):
        stage_red |= drop > 0 and not mul
        wide |= mul and drop > 0
    return stage_red, wide


def _top(p, nb):
    n = p["size"]
    iw, ow, tw = p["input_width"], p["output_width"], p["twiddle_width"]
    sw = p["stage_widths"]
    pipe = p["pipeline"]
    nat = p["output_order"] == "natural"
    mask = n - 1
    L = []
    a = L.append
    ports = ["input clk", "input rst"]
    if p["stall"]:
        ports.append("input en")
    ports += ["input signed [%d:0] in_re" % (iw - 1),
              "input signed [%d:0] in_im" % (iw - 1),
              "output reg signed [%d:0] out_re" % (ow - 1),
              "output reg signed [%d:0] out_im" % (ow - 1),
              "output reg out_valid"]
    a("module fft%d (" % n)
    a(",\n".join("    " + s for s in ports))
    a(");")
    if not p["stall"]:
        a("  wire en = 1'b1;")
    a("  // Free-running sample counter; frame 0 starts at the first enabled")
    a("  // clock after reset. Stage constants below are arrival times (clocks).")
    a("  reg [%d:0] cnt;" % (nb + 1))
    a("  always @(posedge clk) if (rst) cnt <= 0; else if (en) cnt <= cnt + 1'b1;")
    cur, wcur = "in", iw
    t = 0
    _, cmul_wide = _reduction_kinds(p)
    for i, (w, drop, mul) in enumerate(_stage_drops(p)):
        d = n >> (i + 1)
        lgd = nb - 1 - i
        odd = i % 2 == 1
        # A stage B feeding a twiddle multiplier keeps its butterfly output
        # one growth bit wide (ws) so fft_cmul performs the single combined
        # rounding of twiddle fraction + drop; every other stage rounds its
        # drop inside fft_sdf_stage. drop <= 0 everywhere keeps the legacy
        # emission byte for byte.
        ws = wcur + 1 if (mul and drop > 0) else w
        a("  // stage %d: radix-2 butterfly, delay %d" % (i, d))
        if drop > 0:
            a("  //   drops %d LSB%s, %s" % (
                drop, "" if drop == 1 else "s",
                "rounded in the twiddle multiplier that follows" if mul
                else "rounded convergent inside the stage"))
        a("  wire [%d:0] idx%d = cnt[%d:0] - %d'd%d;" % (nb - 1, i, nb - 1, nb, t & mask))
        a("  wire signed [%d:0] s%d_re, s%d_im;" % (ws - 1, i, i))
        half = "idx%d[%d]" % (i, lgd + 1) if odd else "1'b0"
        a("  fft_sdf_stage #(.WI(%d), .W(%d), .D(%d), .ROT(%d), .PIPE(%d)) u_s%d (" % (
            wcur, ws, d, 1 if odd else 0, pipe, i))
        a("      .clk(clk), .en(en), .phase(idx%d[%d]), .half(%s)," % (i, lgd, half))
        a("      .in_re(%s_re), .in_im(%s_im), .out_re(s%d_re), .out_im(s%d_im));" % (cur, cur, i, i))
        t += d + pipe
        cur, wcur = "s%d" % i, ws
        if mul:
            pr = i // 2
            m = n >> (2 * pr)
            lgm = nb - 2 * pr
            a("  // twiddle multiplier after stage %d (block size %d)" % (i, m))
            a("  wire [%d:0] midx%d = cnt[%d:0] - %d'd%d;" % (nb - 1, i, nb - 1, nb, t & mask))
            a("  wire [1:0] q%d = midx%d[%d:%d];" % (i, i, lgm - 1, lgm - 2))
            a("  wire [%d:0] mm%d = midx%d[%d:0];" % (lgm - 3, i, i, lgm - 3))
            a("  wire [%d:0] me%d = (q%d == 2'd1) ? {mm%d, 1'b0} : (q%d == 2'd2) ? mm%d"
              " : (q%d == 2'd3) ? (mm%d + {mm%d, 1'b0}) : %d'd0;" % (
                  nb - 1, i, i, i, i, i, i, i, i, nb))
            a("  wire [%d:0] ma%d = me%d << %d;" % (nb - 1, i, i, 2 * pr))
            a("  wire signed [%d:0] tr%d, ti%d;" % (tw - 1, i, i))
            a("  fft_twrom u_tw%d (.addr(ma%d), .w_re(tr%d), .w_im(ti%d));" % (i, i, i, i))
            a("  wire signed [%d:0] m%d_re, m%d_im;" % (w - 1, i, i))
            if cmul_wide:
                # The shared fft_cmul text carries OW whenever any
                # multiplier absorbs a drop, so every instance passes it;
                # a multiplier without a drop passes W == OW (S == TW-2,
                # the legacy rounding).
                a("  fft_cmul #(.W(%d), .OW(%d), .TW(%d), .MULT3(%d), "
                  ".PIPE(%d)) u_m%d (" % (
                      ws, w, tw, 1 if p["complex_mult"] == "3mult" else 0,
                      pipe, i))
            else:
                a("  fft_cmul #(.W(%d), .TW(%d), .MULT3(%d), .PIPE(%d)) u_m%d (" % (
                    w, tw, 1 if p["complex_mult"] == "3mult" else 0, pipe, i))
            a("      .clk(clk), .en(en), .a_re(s%d_re), .a_im(s%d_im)," % (i, i))
            a("      .w_re(tr%d), .w_im(ti%d), .p_re(m%d_re), .p_im(m%d_im));" % (i, i, i, i))
            t += pipe
            cur = "m%d" % i
            wcur = w
    wl = sw[-1]
    sh = wl - ow
    a("  // final reduction: drop %d LSBs (%s)" % (sh, p["rounding"]))
    a("  wire signed [%d:0] f_re, f_im;" % (ow - 1))
    for c in ("re", "im"):
        a("  fft_rnd #(.W(%d), .S(%d), .CONV(%d)) u_f%s (.x(%s_%s), .y(f_%s));" % (
            wl, sh, 1 if p["rounding"] == "convergent" else 0, c, cur, c, c))
    tout = t
    if nat:
        a("  wire [%d:0] cw = cnt[%d:0] - %d'd%d;" % (nb, nb, nb + 1, tout & (2 * n - 1)))
        a("  wire signed [%d:0] r_re, r_im;" % (ow - 1))
        a("  fft_reorder #(.NB(%d), .W(%d)) u_ro (.clk(clk), .en(en), .cw(cw)," % (nb, ow))
        a("      .din_re(f_re), .din_im(f_im), .dout_re(r_re), .dout_im(r_im));")
        src, tval = "r", tout + n
    else:
        src, tval = "f", tout
    a("  always @(posedge clk) begin")
    a("    if (rst) out_valid <= 1'b0;")
    a("    else if (en) begin")
    a("      if (cnt == %d'd%d) out_valid <= 1'b1;" % (nb + 2, tval))
    a("      out_re <= %s_re;" % src)
    a("      out_im <= %s_im;" % src)
    a("    end")
    a("  end")
    a("endmodule")
    return "\n".join(L) + "\n"


def generate(p):
    """Return {filename: text}, deterministic for equal params."""
    n = p["size"]
    nb = n.bit_length() - 1
    # The reduction-capable module texts are emitted only when a stage
    # actually reduces, so regenerating an unreduced configuration (the
    # production parameter file) stays byte-identical to the legacy
    # emission, shared module text included.
    stage_red, cmul_wide = _reduction_kinds(p)
    files = {
        "fft%d.v" % n: _top(p, nb),
        "fft_cmul.v": _CMUL_RED if cmul_wide else _CMUL,
        "fft_rnd.v": _RND,
        "fft_sdf_stage.v": _STAGE_RED if stage_red else _STAGE,
    }
    if n >= 16:
        files["fft_twrom.v"] = _twrom(p, nb)
    if p["output_order"] == "natural":
        files["fft_reorder.v"] = _REORDER
    return {name: _header(p) + body for name, body in files.items()}


def write_rtl(p, outdir):
    os.makedirs(outdir, exist_ok=True)
    names = []
    for name, text in sorted(generate(p).items()):
        with open(os.path.join(outdir, name), "w", newline="\n") as f:
            f.write(text)
        names.append(name)
    return names
