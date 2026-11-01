"""Bit-accurate fixed-point model of the radix-2^2 SDF FFT (decision 0004).

Integer arithmetic only: samples are int64 numpy arrays, so results are
deterministic and exact. Every SQNR figure printed by the CLI is *simulated*
(this model against the double-precision reference), never *measured*.

Parameter file: the generator's own (schema in rtl/README.md); `load_params`
delegates to the generator's parser (rtl/gen/params.py), so there is one
validator. Widths beyond the generator's ranges are an explicit opt-in: build a
`Params` directly and pass it to `FixedPointFFT`. `key=value` lines, `#`
comments, list values comma-separated. Keys: size, architecture, direction,
output_order, input_width, output_width, stage_widths, twiddle_width,
complex_mult, rounding, pipeline, stall. `pipeline` and `stall` are structural
(registers and enable gating) and are validated but do not change the
arithmetic. There is no overflow key: the model never saturates, it counts and
wraps (see `Stats.overflow`).

Arithmetic contract (the RTL must match it bit for bit):

* Samples are signed two's-complement I/Q components; `size` is a power of 4.
* The data path is the radix-2^2 DIF decomposition, `size = 4^p` giving `2p`
  radix-2 stages. Stages 2k and 2k+1 form a pair over blocks of M samples:
  stage A computes a +/- b between samples M/2 apart; stage B does the same
  between samples M/4 apart inside each half, with the upper-quarter operand of
  the difference half rotated by -j first (a swap and negate, no multiplier).
  After stage B, element n' of sub-block (b1, b2) (b1 = stage A half, b2 =
  stage B half) is multiplied by W_M^(n'*(b1+2*b2)), W_M = exp(-2j*pi/M). The
  last pair (M = 4) needs no multiplier. A 256-point FFT has 3 multipliers.
* `stage_widths[i]` is the width of each component after radix-2 stage i,
  including the twiddle multiplication that follows stage B of a pair. Each
  stage computes exactly in integers, then performs ONE width reduction: it
  drops `max(0, (stage_widths[i-1] + 1) - stage_widths[i])` LSBs plus the
  twiddle fraction bits (stage_widths[-1] is `input_width`). A wider stage
  than that growth only sign-extends. The output stage drops
  `max(0, stage_widths[-1] - output_width)` LSBs. Dropped bits are rounded
  convergent (half to even); `rounding=truncate` (floor) applies only at the
  output stage, as 0002 allows.
* Twiddles are signed `twiddle_width`-bit integers at scale 2^(twiddle_width-2)
  (so 1.0 is exact), built from an eighth-circle table by symmetry.
* No saturation. A component outside its stage's signed range is counted in
  `Stats.overflow`, then wrapped to two's complement like the RTL would;
  `strict=True` raises OverflowError instead.
* Outputs are scaled by 2^-total_shift against the unscaled reference;
  `Result.total_shift` holds that exponent and `candidate` undoes it.
* `output_order=bitrev` is the SDF stream order; `natural` applies the
  bit-reversal permutation.

`complex_mult` (3mult/4mult) is a structure choice with the same exact product,
so it does not change the model's output.
"""

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reference  # noqa: E402
import vectors  # noqa: E402
from rtl.gen import params as generator_params  # noqa: E402

MODEL_ID = "fixedpoint_model r22sdf v1"

# int64 holds a 32-bit component times a 24-bit twiddle.
_WIDTH_MAX = {"input_width": 32, "output_width": 32, "stage_widths": 32, "twiddle_width": 24}


@dataclass(frozen=True)
class Params:
    size: int
    architecture: str
    direction: str
    output_order: str
    input_width: int
    output_width: int
    stage_widths: tuple
    twiddle_width: int
    complex_mult: str
    rounding: str
    pipeline: int
    stall: int
    sha256: str = ""


def load_params(path) -> Params:
    """Read a parameter file with the generator's own parser (rtl/gen/params.py).

    The generator's validation applies unchanged, so the model cannot be asked
    about a configuration no RTL can exist for. ParamError (a ValueError)
    names the bad key. Exploratory widths outside the generator's ranges are
    an explicit opt-in: build a `Params` directly and pass it to `FixedPointFFT`.
    """
    d = generator_params.load_params(path)
    sha = d.pop("_sha256")
    d["stage_widths"] = tuple(d["stage_widths"])
    return Params(sha256=sha, **d)


def check_params(p: Params) -> None:
    """Model-only invariants, applied to every `Params` including exploratory ones.

    The algorithm needs a power-of-4 size and one width per radix-2 stage; int64
    holds a 32-bit component times a 24-bit twiddle, so wider stages would wrap
    inside the model and not like the RTL.
    """
    n = p.size
    if n < 4 or 4 ** (n.bit_length() // 2) != n:
        raise ValueError(f"key 'size': {n} is not a power of 4")
    stages = n.bit_length() - 1
    if len(p.stage_widths) != stages:
        raise ValueError(f"key 'stage_widths': need {stages} entries for size {n}")
    for key, top in _WIDTH_MAX.items():
        for w in (getattr(p, key) if key == "stage_widths" else (getattr(p, key),)):
            if not 2 <= w <= top:
                raise ValueError(f"key {key!r}: width {w} outside 2..{top} the model can hold")


def round_shift(x: np.ndarray, s: int, mode: str = "convergent") -> np.ndarray:
    """Divide by 2^s, rounding half to even (`convergent`) or flooring."""
    if s <= 0:
        return x << -s
    q = x >> s
    if mode == "truncate":
        return q
    r = x - (q << s)
    half = 1 << (s - 1)
    up = (r > half) | ((r == half) & ((q & 1) == 1))
    return q + up.astype(np.int64)


def twiddle_table(m: int, tw: int):
    """(cos, sin) integers for W_m^k = cos - j*sin, k in 0..m-1, scale 2^(tw-2).

    Only the first eighth circle is rounded; the rest follows by symmetry, so
    the table is exactly symmetric like the combinational ROM in the RTL.
    """
    one = 1 << (tw - 2)
    q4 = m // 4
    cos = np.zeros(m, dtype=np.int64)
    sin = np.zeros(m, dtype=np.int64)

    def base(k):  # angle 2*pi*k/m, 0 <= k <= m/8
        a = 2 * math.pi * k / m
        return int(np.rint(math.cos(a) * one)), int(np.rint(math.sin(a) * one))

    for k in range(m):
        quad, kq = divmod(k, q4)
        if 8 * kq <= m:
            c, s = base(kq)
        else:  # mirror about 45 degrees
            s, c = base(q4 - kq)
        for _ in range(quad):  # rotate by 90 degrees
            c, s = -s, c
        cos[k], sin[k] = c, s
    return cos, sin


class Stats:
    """Per-stage overflow counts and peak magnitudes (component values)."""

    def __init__(self, nstages):
        self.overflow = [0] * (nstages + 1)  # last entry: output stage
        self.peak = [0] * (nstages + 1)


@dataclass
class Result:
    re: np.ndarray
    im: np.ndarray
    total_shift: int
    stats: Stats = field(repr=False)

    def scaled(self) -> np.ndarray:
        """Complex128 output at the unscaled reference scale."""
        return (self.re + 1j * self.im) * float(2.0 ** self.total_shift)


def _wrap(x: np.ndarray, width: int) -> np.ndarray:
    lo, mod = -(1 << (width - 1)), 1 << width
    return ((x - lo) % mod) + lo


def _check(x_re, x_im, width, stage, stats, strict):
    lo, hi = -(1 << (width - 1)), (1 << (width - 1)) - 1
    bad = int(np.count_nonzero((x_re < lo) | (x_re > hi)) + np.count_nonzero((x_im < lo) | (x_im > hi)))
    stats.peak[stage] = max(stats.peak[stage], int(max(np.abs(x_re).max(), np.abs(x_im).max())))
    if bad:
        if strict:
            raise OverflowError(f"stage {stage}: {bad} component(s) outside {width}-bit range")
        stats.overflow[stage] += bad
        return _wrap(x_re, width), _wrap(x_im, width)
    return x_re, x_im


class FixedPointFFT:
    def __init__(self, params: Params, strict: bool = False):
        check_params(params)
        self.p = params
        self.strict = strict
        self.stats = Stats(len(params.stage_widths))
        self._tw = {}

    @classmethod
    def from_file(cls, path, strict: bool = False):
        return cls(load_params(path), strict)

    def _twiddles(self, m):
        if m not in self._tw:
            self._tw[m] = twiddle_table(m, self.p.twiddle_width)
        return self._tw[m]

    def run(self, re: np.ndarray, im: np.ndarray) -> Result:
        """Transform integer I/Q frames of shape (frames, size) or (size,)."""
        p = self.p
        re = np.asarray(re, dtype=np.int64)
        im = np.asarray(im, dtype=np.int64)
        squeeze = re.ndim == 1
        re, im = np.atleast_2d(re), np.atleast_2d(im)
        if re.shape != im.shape or re.shape[-1] != p.size:
            raise ValueError(f"frames must have {p.size} samples, got {re.shape}")
        lim = 1 << (p.input_width - 1)
        if (re < -lim).any() or (re >= lim).any() or (im < -lim).any() or (im >= lim).any():
            raise ValueError(f"input outside {p.input_width}-bit signed range")
        f = re.shape[0]
        total_shift = 0
        wprev = p.input_width
        m = p.size
        stage = 0
        # Blocks: (frames, nblocks, m)
        re = re.reshape(f, 1, m)
        im = im.reshape(f, 1, m)
        while m >= 4:
            h, q = m // 2, m // 4
            # stage A
            ar = np.concatenate([re[..., :h] + re[..., h:], re[..., :h] - re[..., h:]], axis=-1)
            ai = np.concatenate([im[..., :h] + im[..., h:], im[..., :h] - im[..., h:]], axis=-1)
            re, im, wprev, total_shift = self._reduce(ar, ai, stage, wprev, total_shift, 0)
            stage += 1
            nb = re.shape[1]
            # stage B on the 2*nb halves (sum halves then difference halves, each length h)
            halves_r = re.reshape(f, nb, 2, h)
            halves_i = im.reshape(f, nb, 2, h)
            tr, ti = halves_r[..., :q], halves_i[..., :q]
            ur, ui = halves_r[..., q:], halves_i[..., q:]
            # -j * (ur + j ui) = ui - j ur on the difference half only
            rot_r = ur.copy()
            rot_i = ui.copy()
            rot_r[:, :, 1] = ui[:, :, 1]
            rot_i[:, :, 1] = -ur[:, :, 1]
            br = np.concatenate([tr + rot_r, tr - rot_r], axis=-1)
            bi = np.concatenate([ti + rot_i, ti - rot_i], axis=-1)
            # twiddle: sub-block c' = 2*b1+b2 in memory, factor index n'*(b1+2*b2)
            shift_extra = 0
            if m > 4:
                cos, sin = self._twiddles(m)
                nprime = np.arange(q)
                rows_r, rows_i = [], []
                for b1 in (0, 1):
                    for b2 in (0, 1):
                        c = (nprime * (b1 + 2 * b2)) % m
                        wr, wi = cos[c], -sin[c]
                        xr = br[:, :, b1, b2 * q:(b2 + 1) * q]
                        xi = bi[:, :, b1, b2 * q:(b2 + 1) * q]
                        rows_r.append(xr * wr - xi * wi)
                        rows_i.append(xr * wi + xi * wr)
                br = np.stack(rows_r, axis=2).reshape(f, nb, 2, 2 * q)
                bi = np.stack(rows_i, axis=2).reshape(f, nb, 2, 2 * q)
                shift_extra = p.twiddle_width - 2
            re = br.reshape(f, nb * 4, q)
            im = bi.reshape(f, nb * 4, q)
            re, im, wprev, total_shift = self._reduce(re, im, stage, wprev, total_shift, shift_extra)
            stage += 1
            m = q
        re = re.reshape(f, p.size)
        im = im.reshape(f, p.size)
        # Output stage: one reduction to output_width (rounding mode applies here)
        osh = max(0, wprev - p.output_width)
        re = round_shift(re, osh, p.rounding)
        im = round_shift(im, osh, p.rounding)
        total_shift += osh
        # A rounding carry can step past the top code, so this is checked too.
        re, im = _check(re, im, p.output_width, len(p.stage_widths), self.stats, self.strict)
        if p.output_order == "natural":
            perm = _bitrev_perm(p.size)
            re, im = re[:, perm], im[:, perm]
        if squeeze:
            re, im = re[0], im[0]
        return Result(re, im, total_shift, self.stats)

    def _reduce(self, xr, xi, stage, wprev, total_shift, frac_bits):
        """Single width reduction after a stage: drop growth LSBs and twiddle fraction."""
        w = self.p.stage_widths[stage]
        drop = max(0, wprev + 1 - w)
        xr = round_shift(xr, drop + frac_bits, "convergent")
        xi = round_shift(xi, drop + frac_bits, "convergent")
        xr, xi = _check(xr, xi, w, stage, self.stats, self.strict)
        return xr, xi, w, total_shift + drop

    def candidate(self, frame: np.ndarray) -> np.ndarray:
        """Plug-in for `reference.set_sqnr_db`: complex frame in, scaled out.

        The output is returned in natural order regardless of `output_order`
        (a bit-reversed stream is un-permuted so it can be scored).
        """
        frame = np.asarray(frame)
        res = self.run(np.rint(frame.real).astype(np.int64), np.rint(frame.imag).astype(np.int64))
        out = res.scaled()
        if self.p.output_order == "bitrev":
            out = out[_bitrev_perm(self.p.size)]
        return out


def _bitrev_perm(n: int) -> np.ndarray:
    bits = n.bit_length() - 1
    return np.array([int(format(i, f"0{bits}b")[::-1], 2) for i in range(n)])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 -m sim.fixedpoint_model <params-file>", file=sys.stderr)
        return 2
    model = FixedPointFFT.from_file(argv[0])
    p = model.p
    print(f"model:   {MODEL_ID}")
    print(f"params:  {argv[0]} sha256={p.sha256}")
    print(f"config:  size={p.size} in={p.input_width} stages={list(p.stage_widths)} "
          f"out={p.output_width} tw={p.twiddle_width} round={p.rounding} order={p.output_order}")
    print("SQNR (SIMULATED, min over frames, model vs double-precision reference):")
    for name in vectors.VECTOR_SETS:
        frames = vectors.generate_frames(name, n=p.size, width=p.input_width)
        model.stats = Stats(len(p.stage_widths))
        sq = reference.set_sqnr_db(frames, model.candidate)
        ovf = sum(model.stats.overflow)
        print(f"  {name:9s} {sq:7.2f} dB   overflow components: {ovf}   "
              f"peak/stage: {model.stats.peak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
