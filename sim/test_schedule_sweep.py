"""Tests for the candidate growth-schedule sweep, with two negative controls.

Run through `make -C verification fxp-model`.

The controls are on the two axes the sweep actually measures:

* `stage_widths` really does move the SQNR column (a sweep that ignored its
  candidate table would report one figure for every row);
* the overflow column is wired to the model's `Stats` rather than hard-coded to
  the zero it legitimately reports for every candidate.

The second control is AMPLITUDE driven, not schedule driven, and that is not a
weaker control -- it is the only one this model admits. No `stage_widths` /
`twiddle_width` schedule overflows on the spec vector sets: each stage performs
exactly one reduction dropping `max(0, (stage_widths[i-1] + 1) - stage_widths[i])`
LSBs, so a narrow stage is scale-compensated and a wide one only sign-extends.
`test_overflow_range.py:test_width_change_moves_range_negative_control` records
the same mechanism from the other direction. Driving the sweep's own scoring
path with full-scale frames (where the placeholder does overflow, first in
stage 1) proves the column reports what the model counted.
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

from sim import fixedpoint_model as fm
from sim import schedule_sweep as ss
from sim import vectors

PARAMS = Path(__file__).resolve().parent.parent / "rtl" / "params" / "fft256.params"
FRAMES = 20  # fewer frames keep the tests quick; the committed record uses 100

# AC 4's small size: 16 points is 4 radix-2 stages and generator-legal.
SMALL_SIZE = 16
SMALL_CANDIDATES = (
    {"name": "small, 1 bit/stage", "stage_widths": (17, 18, 19, 20),
     "twiddle_width": 16, "note": "small-size analogue of the committed placeholder"},
    {"name": "small, flat at input+1", "stage_widths": (17, 17, 17, 17),
     "twiddle_width": 16, "note": "one guard bit, no growth"},
    {"name": "small, zero growth", "stage_widths": (16, 16, 16, 16),
     "twiddle_width": 16, "note": "narrowest generator-legal schedule"},
)


def _small_base():
    """The committed parameters re-sized to `SMALL_SIZE` (4 stages)."""
    base = fm.load_params(PARAMS)
    return fm.Params(**dict(base.__dict__, size=SMALL_SIZE,
                            stage_widths=SMALL_CANDIDATES[0]["stage_widths"]))


def test_small_size_sweep_reports_every_candidate():
    res = ss.sweep(_small_base(), SMALL_CANDIDATES, 10)
    assert len(res) == len(SMALL_CANDIDATES), f"expected one row per candidate, got {len(res)}"
    for r, cand in zip(res, SMALL_CANDIDATES):
        assert r["name"] == cand["name"], f"rows out of order: {r['name']} vs {cand['name']}"
        assert r["stage_widths"] == list(cand["stage_widths"]), r
        assert r["width_sum"] == sum(cand["stage_widths"]), r
        assert r["generator_legal"] and r["generator_error"] is None, r
        assert set(r["sets"]) == set(vectors.VECTOR_SETS), r["sets"].keys()
        # AC 2's three figures are present and real for every vector set.
        for name, s in r["sets"].items():
            assert s["min_sqnr_db"] > 0, f"{r['name']}/{name}: {s}"
            assert s["overflow_components"] == 0, f"{r['name']}/{name}: {s}"
    # The candidates differ, so their figures must differ: a sweep returning one
    # number for every row would pass every assertion above.
    figures = [round(r["min_sqnr_db"], 6) for r in res]
    assert len(set(figures)) == len(figures), f"candidates scored identically: {figures}"


def test_overflow_column_is_wired_negative_control():
    """The overflow column must report what the model counted, not a hard-coded 0.

    Amplitude driven by necessity (see the module docstring): no schedule
    overflows on the spec sets, so the control feeds the sweep's own
    `score_frames` full-scale frames of the same kind as `random50` and
    requires a non-zero count, then requires 0 on the spec set itself.
    """
    base = fm.load_params(PARAMS)
    p = ss.candidate_params(base, ss.CANDIDATES[0])
    model = fm.FixedPointFFT(p)
    full = vectors.generate_swept_frames(vectors.VECTOR_SETS["random50"], 1.00,
                                         n=p.size, width=p.input_width, frames=FRAMES)
    hot = ss.score_frames(model, full)
    assert hot["overflow_components"] > 0, (
        f"full-scale frames reported no overflow ({hot}); the overflow column is "
        "not wired to the model's Stats")
    spec_set = vectors.generate_frames("random50", n=p.size, width=p.input_width,
                                       frames=FRAMES)
    cool = ss.score_frames(model, spec_set)
    assert cool["overflow_components"] == 0, (
        f"the spec set overflowed ({cool}); Stats was not reset between sets")


def test_sqnr_column_separates_schedules_negative_control():
    """`stage_widths` must move the SQNR column, and not in the naive direction.

    `front-loaded growth` has the LARGEST width sum of any candidate and the
    worst accuracy. A sweep insensitive to `stage_widths`, or one ranking by
    width sum, fails here.
    """
    base = fm.load_params(PARAMS)
    placeholder = ss.evaluate(base, ss.CANDIDATES[0], 10)
    front = ss.evaluate(base, next(c for c in ss.CANDIDATES
                                   if c["name"] == "front-loaded growth"), 10)
    assert front["width_sum"] > placeholder["width_sum"], (front, placeholder)
    gap = placeholder["min_sqnr_db"] - front["min_sqnr_db"]
    assert gap > 10.0, (
        f"the sweep separated the two schedules by only {gap:.2f} dB; it is not "
        "responding to stage_widths")
    assert placeholder["meets_spec_sqnr_target"] and not front["meets_spec_sqnr_target"], (
        f"the spec target verdict is wrong: {placeholder['min_sqnr_db']:.2f} dB vs "
        f"{front['min_sqnr_db']:.2f} dB against {ss.SPEC_SQNR_TARGET_DB} dB")


def test_generator_illegal_candidate_is_flagged_not_silently_studied():
    illegal = {"name": "decreasing widths", "stage_widths": (20, 19, 18, 18),
               "twiddle_width": 16, "note": "deliberately generator-illegal"}
    r = ss.evaluate(_small_base(), illegal, 5)
    assert r["generator_legal"] is False, r
    assert "stage_widths" in (r["generator_error"] or ""), r["generator_error"]
    # It is still scored, so the record shows why it was rejected and what it cost.
    assert r["sets"] and all(s["min_sqnr_db"] > 0 for s in r["sets"].values()), r
    legal = ss.evaluate(_small_base(), SMALL_CANDIDATES[0], 5)
    assert legal["generator_legal"] is True and legal["generator_error"] is None, legal


def test_committed_candidates_are_all_generator_legal():
    base = fm.load_params(PARAMS)
    for cand in ss.CANDIDATES:
        p = ss.candidate_params(base, cand)
        legal, reason = ss.generator_verdict(p)
        assert legal, f"{cand['name']} is not generator-legal: {reason}"
        assert len(p.stage_widths) == len(base.stage_widths), cand["name"]
    # AC 3: the committed placeholder, and at least one schedule growing by less
    # than one bit per stage, are both in the table.
    names = [c["name"] for c in ss.CANDIDATES]
    assert any(tuple(c["stage_widths"]) == tuple(base.stage_widths)
               and c["twiddle_width"] == base.twiddle_width
               for c in ss.CANDIDATES), f"the committed placeholder is missing: {names}"
    assert any(sum(c["stage_widths"]) < sum(base.stage_widths) for c in ss.CANDIDATES), (
        f"no candidate grows by less than one bit per stage: {names}")


def test_candidate_params_do_not_claim_a_file_hash():
    """A candidate inherits the BASE file's sha256; the record must say so once."""
    base = fm.load_params(PARAMS)
    other = ss.candidate_params(base, ss.CANDIDATES[1])
    assert other.stage_widths != base.stage_widths, "pick a candidate that differs"
    assert other.sha256 == base.sha256, "candidate_params changed the inherited hash"
    res = ss.sweep(_small_base(), SMALL_CANDIDATES[:1], 5)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        rec = ss.record(path, PARAMS, base, res, 5)
    assert rec["parameter_file_sha256"] == base.sha256
    assert all("sha256" not in c for c in rec["candidates"]), (
        "a per-candidate sha256 would assert a hash for a file that does not exist")


def test_record_is_append_only():
    base = fm.load_params(PARAMS)
    res = ss.sweep(_small_base(), SMALL_CANDIDATES[:1], 5)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        ss.record(path, PARAMS, base, res, 5)
        first = json.loads(path.read_text())["records"][0]
        ss.record(path, PARAMS, base, res, 5)
        data = json.loads(path.read_text())
    assert len(data["records"]) == 2, data
    assert data["records"][0] == first, "the earlier record was modified"
    assert "SIMULATED" in data["records"][0]["note"]
    assert data["records"][0]["model"] == fm.MODEL_ID


def test_record_json_is_strict_no_infinity():
    """`json.dumps(float('inf'))` emits a bare `Infinity`, which is not valid JSON."""
    assert ss._json_safe(float("inf")) == "inf"
    assert ss._json_safe(float("-inf")) == "-inf"
    assert ss._json_safe(float("nan")) is None
    base = fm.load_params(PARAMS)
    res = ss.sweep(_small_base(), SMALL_CANDIDATES[:1], 5)
    # An exact match is unreachable at these sizes, so force one.
    res[0]["sets"][next(iter(res[0]["sets"]))]["min_sqnr_db"] = float("inf")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        ss.record(path, PARAMS, base, res, 5)
        text = path.read_text()

    def _bare(token):  # only called for a non-finite JSON literal
        raise AssertionError(f"the record carries a bare {token} literal, "
                             "which strict JSON readers reject")

    json.loads(text, parse_constant=_bare)
    assert '"inf"' in text
    # A plain `grep -E 'Infinity|NaN'` of a committed record must also find
    # nothing, so the record's own prose must not use those words either.
    assert "Infinity" not in text and "NaN" not in text, text


def test_main_states_simulated_and_selects_nothing():
    saved = ss.FRAMES
    ss.FRAMES = 2  # the full 100-frame run is the committed record's job
    try:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = ss.main([str(PARAMS), "--record", str(path)])
            text = out.getvalue()
            records = json.loads(path.read_text())["records"]
    finally:
        ss.FRAMES = saved
    assert rc == 0, rc
    assert "SIMULATED" in text, text
    assert "no schedule is selected here" in text, text
    assert len(records) == 1 and records[0]["frames_per_set"] == 2, records
    assert len(records[0]["candidates"]) == len(ss.CANDIDATES)
    for cand in ss.CANDIDATES:
        assert cand["name"] in text, f"{cand['name']} missing from the printed table"


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
