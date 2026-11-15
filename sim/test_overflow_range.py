"""Tests for the no-overflow amplitude sweep, with a narrowed-width control.

Run through `make -C verification fxp-model`.
"""

import contextlib
import io
import sys
import tempfile
from pathlib import Path

from sim import fixedpoint_model as fm
from sim import overflow_range as orr
from sim import vectors

PARAMS = Path(__file__).resolve().parent.parent / "rtl" / "params" / "fft256.params"
FRAMES = 20  # fewer frames keep the tests quick; the committed record uses 100


def test_fixed_sets_unchanged_by_swept_generator():
    for name, spec in vectors.VECTOR_SETS.items():
        a = vectors.generate_frames(name, frames=8)
        b = vectors.generate_swept_frames(spec, spec["fraction"], frames=8)
        assert (a == b).all(), f"swept generator differs from generate_frames for {name}"


def test_committed_params_range_and_labels():
    p = fm.load_params(PARAMS)
    res = orr.sweep(p, FRAMES)
    rnd, tone = res["random"], res["tone"]
    assert rnd["max_no_overflow_fraction"] is not None and rnd["max_no_overflow_fraction"] >= 0.7
    assert rnd["first_overflow_stage"] is not None
    # Every figure at or below the max must really be clean (strict model raises).
    for f in orr.fractions():
        if f > rnd["max_no_overflow_fraction"]:
            break
        data = vectors.generate_swept_frames(orr.KINDS["random"], f, frames=FRAMES)
        fm.FixedPointFFT(p, strict=True).run(data.real.astype("int64"), data.imag.astype("int64"))
    assert tone["max_no_overflow_fraction"] >= 0.9, "tone90 must not overflow (spec ruling)"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert orr.main([str(PARAMS)]) == 0
    assert "SIMULATED" in out.getvalue() and "PLACEHOLDER" in out.getvalue()


def _with_width(p, stage, delta):
    w = list(p.stage_widths)
    w[stage] += delta
    return fm.Params(**dict(p.__dict__, stage_widths=tuple(w)))


def test_width_change_moves_range_negative_control():
    """The sweep must respond to `stage_widths`.

    Narrowing alone does not lower the range in this model: a narrower stage
    drops one more LSB (`max(0, wprev + 1 - w)`), so the pre-shift overflow
    threshold is unchanged and the range is the same. The sensitive direction
    is widening the twiddle stage that overflows first (stage 1): it adds
    headroom, so the range must rise, and the first overflow must move later
    or vanish. A sweep that ignored the widths would fail this.
    """
    p = fm.load_params(PARAMS)
    base = orr.sweep_kind(p, orr.KINDS["random"], FRAMES)
    assert base["first_overflow_stage"] == "stage 1", base
    wide = orr.sweep_kind(_with_width(p, 1, +1), orr.KINDS["random"], FRAMES)
    assert wide["max_no_overflow_fraction"] > base["max_no_overflow_fraction"], (
        f"widening stage 1 did not raise the range ({base} -> {wide}); sweep is insensitive")
    assert wide["first_overflow_stage"] != "stage 1", wide
    # Narrowing stage 1 is scale-compensated: same threshold, same stage.
    narrow = orr.sweep_kind(_with_width(p, 1, -1), orr.KINDS["random"], FRAMES)
    assert narrow["first_overflow_stage"] == "stage 1", narrow


def test_record_is_append_only():
    p = fm.load_params(PARAMS)
    res = {"tone": {"max_no_overflow_fraction": 1.0, "first_overflow_fraction": None,
                    "first_overflow_stage": None, "bound": "at_least_sweep_end"}}
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        orr.record(path, PARAMS, p, res)
        orr.record(path, PARAMS, p, res)
        import json
        data = json.loads(path.read_text())
        assert len(data["records"]) == 2
        assert data["records"][0]["parameter_file_sha256"] == p.sha256


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
