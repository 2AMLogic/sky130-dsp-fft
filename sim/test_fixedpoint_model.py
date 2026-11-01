"""Tests for the bit-accurate fixed-point FFT model.

Run through `make -C verification fxp-model`. FXP_MUTANT=floor_ties swaps the
convergent rounder for a flooring one so the negative control reuses the same
tests.
"""

import contextlib
import io
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fixedpoint_model as fm  # noqa: E402
import reference  # noqa: E402
import vectors  # noqa: E402

if os.environ.get("FXP_MUTANT") == "floor_ties":
    _orig_round_shift = fm.round_shift
    fm.round_shift = lambda x, s, mode="convergent": _orig_round_shift(x, s, "truncate")

TEMPLATE = {
    "size": "256", "architecture": "r22sdf", "direction": "forward",
    "output_order": "natural", "input_width": "16", "output_width": "16",
    "stage_widths": "17,18,19,20,21,22,23,24", "twiddle_width": "16",
    "complex_mult": "4mult", "rounding": "convergent", "pipeline": "1", "stall": "1",
}
# Exact-ish small configs: widths grow 1 bit/stage, output keeps every bit.
SMALL = dict(TEMPLATE, size="16", input_width="8", output_width="12",
             stage_widths="9,10,11,12", twiddle_width="24")
TIE = dict(TEMPLATE, size="4", input_width="8", output_width="9", stage_widths="9,10",
           twiddle_width="16")


def write_params(cfg, tmpdir):
    path = Path(tmpdir) / "t.params"
    path.write_text("# test\n" + "".join(f"{k}={v}\n" for k, v in cfg.items()))
    return path


def model(cfg, strict=False):
    with tempfile.TemporaryDirectory() as d:
        return fm.FixedPointFFT.from_file(write_params(cfg, d), strict)


def run1(mod, x):
    r = mod.run(x.real.astype(np.int64), x.imag.astype(np.int64))
    return r.scaled()


def test_impulse_dc_tone_against_double_precision():
    mod = model(SMALL)
    n = 16
    imp = np.zeros(n, dtype=complex)
    imp[0] = 100
    assert np.array_equal(run1(mod, imp), np.full(n, 100 + 0j)), "impulse at 0 must be flat"
    dc = np.full(n, 7 + 3j)
    want = np.zeros(n, dtype=complex)
    want[0] = n * (7 + 3j)
    assert np.array_equal(run1(mod, dc), want), "DC must land exactly in bin 0"
    k = 3
    tone = np.rint(100 * np.exp(2j * np.pi * k * np.arange(n) / n))
    got = run1(mod, tone)
    # Each twiddle stage rounds to an integer, so allow a few LSBs.
    assert np.max(np.abs(got - np.fft.fft(tone))) < 4, "tone differs from double precision"
    assert np.argmax(np.abs(got)) == k


def test_matches_double_precision_at_256():
    mod = model(TEMPLATE)
    x = vectors.generate_frames("random50", frames=1)[0]
    err = np.max(np.abs(mod.candidate(x) - np.fft.fft(x)))
    # Output drops 8 LSBs: half-step 128 per component bounds the error.
    assert err <= 128 * math.sqrt(2) + 1, f"model error {err} beyond the output rounding step"


def test_convergent_rounding_at_a_tie():
    # An impulse of v gives v in every bin; the output drops one bit, so v/2 is a tie.
    for rounding, want in (("convergent", [0, 2, 0, -2]), ("truncate", [0, 1, -1, -2])):
        mod = model(dict(TIE, rounding=rounding))
        got = []
        for v in (1, 3, -1, -3):
            r = mod.run(np.array([v, 0, 0, 0]), np.zeros(4, dtype=np.int64))
            assert r.total_shift == 1
            assert np.all(r.re == r.re[0]), "impulse must be flat"
            got.append(int(r.re[0]))
        assert got == want, f"convergent tie rounding wrong for {rounding}: {got} != {want}"


def test_overflow_is_reported_not_silent():
    cfg = dict(TIE, stage_widths="8,9", output_width="9")
    x = np.array([127, 0, -128, 0])
    mod = model(cfg)
    r = mod.run(x, np.zeros(4, dtype=np.int64))
    assert mod.stats.overflow[0] >= 1, "255/2 rounds up to 128 and must be counted"
    assert r.stats is mod.stats
    strict = model(cfg, strict=True)
    try:
        strict.run(x, np.zeros(4, dtype=np.int64))
    except OverflowError:
        return
    raise AssertionError("strict mode must raise on overflow")


def test_bitrev_is_the_stream_order():
    nat = model(SMALL)
    rev = model(dict(SMALL, output_order="bitrev"))
    x = np.rint(30 * np.random.default_rng(5).standard_normal(16)) + 1j * np.rint(
        30 * np.random.default_rng(6).standard_normal(16))
    a = nat.run(x.real.astype(np.int64), x.imag.astype(np.int64))
    b = rev.run(x.real.astype(np.int64), x.imag.astype(np.int64))
    perm = fm._bitrev_perm(16)
    assert np.array_equal(a.re, b.re[perm]) and np.array_equal(a.im, b.im[perm])


def test_64_point_fallback():
    cfg = dict(TEMPLATE, size="64", input_width="12", output_width="12",
               stage_widths="13,14,15,16,17,18", twiddle_width="18")
    mod = model(cfg)
    x = vectors.generate_frames("tone50", n=64, width=12, frames=1)[0]
    err = np.max(np.abs(mod.candidate(x) - np.fft.fft(x)))
    assert err <= 32 * math.sqrt(2) + 1, f"64-point error {err}"


def test_twiddle_table_symmetry():
    cos, sin = fm.twiddle_table(64, 16)
    one = 1 << 14
    assert (cos[0], sin[0]) == (one, 0) and (cos[16], sin[16]) == (0, one)
    assert (cos[32], sin[32]) == (-one, 0)
    for k in range(64):
        assert cos[k] == sin[(16 - k) % 64] , f"quarter-turn symmetry broken at {k}"
    assert np.max(np.abs(cos - np.rint(one * np.cos(2 * np.pi * np.arange(64) / 64)))) <= 1


def test_params_validation_names_the_key():
    bad = [
        (dict(TEMPLATE, size="128"), "size"),
        (dict(TEMPLATE, input_width="3"), "input_width"),
        (dict(TEMPLATE, stage_widths="17,18"), "stage_widths"),
        (dict(TEMPLATE, rounding="floor"), "rounding"),
        (dict(TEMPLATE, direction="inverse"), "direction"),
        (dict(TEMPLATE, twiddle_width="x"), "twiddle_width"),
        (dict(TEMPLATE, input_width="40"), "input_width"),
        (dict(TEMPLATE, stall="2"), "stall"),
    ]
    for cfg, key in bad:
        try:
            model(cfg)
        except ValueError as e:
            assert key in str(e), f"error for {key} does not name it: {e}"
        else:
            raise AssertionError(f"invalid {key} accepted")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "u.params"
        p.write_text("".join(f"{k}={v}\n" for k, v in TEMPLATE.items()) + "bogus=1\n")
        try:
            fm.load_params(p)
        except ValueError as e:
            assert "bogus" in str(e)
        else:
            raise AssertionError("unknown key accepted")


def test_deterministic_outputs_and_sqnr():
    frames = vectors.generate_frames("random70", frames=5)
    outs, sqnrs = [], []
    for _ in range(2):
        mod = model(TEMPLATE)
        outs.append(b"".join(mod.run(f.real.astype(np.int64), f.imag.astype(np.int64)).re.tobytes() for f in frames))
        sqnrs.append(reference.set_sqnr_db(frames, mod.candidate))
    assert outs[0] == outs[1], "model output not deterministic"
    assert sqnrs[0] == sqnrs[1], "SQNR not deterministic"


def test_sqnr_near_output_quantisation_floor():
    # Only the output rounding (step 256) should matter: error power 2*256^2/12.
    frames = vectors.generate_frames("random50", frames=10)
    got = reference.set_sqnr_db(frames, model(TEMPLATE).candidate)
    sig = np.mean([np.mean(np.abs(reference.reference_fft(f)) ** 2) for f in frames])
    expect = 10 * math.log10(sig / (2 * 256 ** 2 / 12))
    assert abs(got - expect) < 1.5, f"SQNR {got:.2f} dB not near {expect:.2f} dB"


def test_cli_labels_simulated_and_prints_config():
    with tempfile.TemporaryDirectory() as d:
        path = write_params(TEMPLATE, d)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert fm.main([str(path)]) == 0
    out = buf.getvalue()
    assert "SIMULATED" in out and "sha256=" in out and fm.MODEL_ID in out
    for name in vectors.VECTOR_SETS:
        assert name in out, f"{name} missing from the report"


def test_loads_committed_generator_params():
    # AC1 of #31: the model takes the generator's own parameter file.
    path = Path(__file__).resolve().parent.parent / "rtl" / "params" / "fft256.params"
    p = fm.load_params(path)
    assert (p.size, p.complex_mult, p.pipeline, p.stall) == (256, p.complex_mult, 1, 1)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert fm.main([str(path)]) == 0
    assert p.sha256 in buf.getvalue()


def test_wide_widths_accepted():
    # The generator allows 32-bit input/output widths; the loader must too.
    cfg = dict(TEMPLATE, size="4", input_width="32", output_width="32",
               stage_widths="32,32")
    assert model(cfg).p.input_width == 32


def test_exploratory_widths_are_opt_in():
    # A width the generator rejects is refused from a file, and reachable only
    # by building Params directly; the model's own invariants still apply.
    cfg = dict(TEMPLATE, size="4", input_width="3", output_width="3", stage_widths="3,3")
    try:
        model(cfg)
    except ValueError as e:
        assert "input_width" in str(e)
    else:
        raise AssertionError("generator-invalid width accepted from a file")
    p = fm.Params(size=4, architecture="r22sdf", direction="forward", output_order="natural",
                  input_width=3, output_width=3, stage_widths=(3, 3), twiddle_width=8,
                  complex_mult="4mult", rounding="convergent", pipeline=0, stall=0)
    assert fm.FixedPointFFT(p).p.input_width == 3
    for bad in (dict(stage_widths=(3, 40)), dict(size=8), dict(stage_widths=(3,))):
        try:
            fm.FixedPointFFT(fm.Params(**dict(p.__dict__, **bad)))
        except ValueError:
            continue
        raise AssertionError(f"model invariant not enforced for {bad}")


def main() -> int:
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
