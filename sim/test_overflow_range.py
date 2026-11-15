"""Tests for the no-overflow amplitude sweep, with a narrowed-width control.

Run through `make -C verification fxp-model`.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from sim import fixedpoint_model as fm
from sim import overflow_range as orr
from sim import vectors

PARAMS = Path(__file__).resolve().parent.parent / "rtl" / "params" / "fft256.params"
FRAMES = 20  # fewer frames keep the tests quick; the committed record uses 100


def _with_width(p, stage, delta):
    w = list(p.stage_widths)
    w[stage] += delta
    return fm.Params(**dict(p.__dict__, stage_widths=tuple(w)))


class AmplitudeSweep(unittest.TestCase):
    def test_fixed_sets_unchanged_by_swept_generator(self):
        for name, spec in vectors.VECTOR_SETS.items():
            a = vectors.generate_frames(name, frames=8)
            b = vectors.generate_swept_frames(spec, spec["fraction"], frames=8)
            assert (a == b).all(), f"swept generator differs from generate_frames for {name}"

    def test_committed_params_range_and_labels(self):
        p = fm.load_params(PARAMS)
        res = orr.sweep(p, FRAMES)
        rnd, tone = res["random"], res["tone"]
        assert rnd["max_no_overflow_fraction"] is not None and rnd["max_no_overflow_fraction"] >= 0.7
        assert rnd["first_overflow_stage"] is not None
        # Every figure at or below the max must really be clean (strict model raises).
        for f in orr.fractions():
            if f > rnd["max_no_overflow_fraction"]:
                break
            data = vectors.generate_swept_frames(vectors.sweep_specs()["random"], f, frames=FRAMES)
            fm.FixedPointFFT(p, strict=True).run(data.real.astype("int64"), data.imag.astype("int64"))
        assert tone["max_no_overflow_fraction"] >= 0.9, "tone90 must not overflow (spec ruling)"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert orr.main([str(PARAMS)]) == 0
        assert "SIMULATED" in out.getvalue() and "PLACEHOLDER" in out.getvalue()

    def test_width_change_moves_range_negative_control(self):
        """The sweep must respond to `stage_widths`.

        Narrowing alone does not lower the range in this model: a narrower stage
        drops one more LSB (`max(0, wprev + 1 - w)`), so the pre-shift overflow
        threshold is unchanged and the range is the same. The sensitive direction
        is widening the twiddle stage that overflows first (stage 1): it adds
        headroom, so the range must rise, and the first overflow must move later
        or vanish. A sweep that ignored the widths would fail this.
        """
        p = fm.load_params(PARAMS)
        base = orr.sweep_kind(p, vectors.sweep_specs()["random"], FRAMES)
        assert base["first_overflow_stage"] == "stage 1", base
        wide = orr.sweep_kind(_with_width(p, 1, +1), vectors.sweep_specs()["random"], FRAMES)
        assert wide["max_no_overflow_fraction"] > base["max_no_overflow_fraction"], (
            f"widening stage 1 did not raise the range ({base} -> {wide}); sweep is insensitive")
        assert wide["first_overflow_stage"] != "stage 1", wide
        # Narrowing stage 1 is scale-compensated: same threshold, same stage.
        narrow = orr.sweep_kind(_with_width(p, 1, -1), vectors.sweep_specs()["random"], FRAMES)
        assert narrow["first_overflow_stage"] == "stage 1", narrow

    def test_record_carries_params_and_note(self):
        """The sweep's own record fields. The append-only invariant and its
        full-strength test moved onto the shared writer (`sim/records.py`,
        `test_records.py`); the weaker `len == 2` copy that stood here before is
        retired with the duplication it tested."""
        p = fm.load_params(PARAMS)
        res = {"tone": {"max_no_overflow_fraction": 1.0, "first_overflow_fraction": None,
                        "first_overflow_stage": None, "bound": "at_least_sweep_end"}}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            rec = orr.record(path, PARAMS, p, res)
            data = json.loads(path.read_text())
        assert data["records"] == [rec], data
        assert rec["parameter_file_sha256"] == p.sha256
        assert "SIMULATED" in rec["note"]

    def test_derived_random_seeds_are_the_vector_sets_union(self):
        union = set()
        for spec in vectors.VECTOR_SETS.values():
            if spec["kind"] == "random":
                union.update(spec["seeds"])
        specs = vectors.sweep_specs()
        assert specs["random"]["seeds"] == sorted(union)
        assert "seed" not in specs["random"], specs["random"]
        assert specs["tone"]["seed"] == 1
        assert "seeds" not in specs["tone"], specs["tone"]

    def test_sweep_specs_raise_when_a_kind_mixes_seed_keys(self):
        """A kind carrying both `seeds` and scalar `seed` must raise in either
        table order: the generator reads `seeds` while `_provenance()` would
        record only `[seed]`, so the record describes stimulus never generated."""
        original = dict(vectors.VECTOR_SETS)
        mixed = {"kind": "random", "fraction": 0.8, "seed": 99}

        def assert_mixed_key_raise(exc):
            assert ("random" in str(exc) and "seeds" in str(exc)
                    and "scalar 'seed'" in str(exc)), exc

        try:
            vectors.VECTOR_SETS["random80"] = mixed
            try:
                vectors.sweep_specs()
            except ValueError as e:
                assert_mixed_key_raise(e)
            else:
                assert False, "sweep_specs did not raise on mixed seed keys"
            rebuilt = {"random80": mixed}
            rebuilt.update(original)
            vectors.VECTOR_SETS.clear()
            vectors.VECTOR_SETS.update(rebuilt)
            try:
                vectors.sweep_specs()
            except ValueError as e:
                assert_mixed_key_raise(e)
            else:
                assert False, "sweep_specs did not raise when 'seed' precedes 'seeds'"
        finally:
            vectors.VECTOR_SETS.clear()
            vectors.VECTOR_SETS.update(original)

    def test_provenance_refuses_mixed_seed_keys_but_keeps_scalar_seed(self):
        with self.assertRaises(ValueError):
            orr._provenance({"kind": "random", "seeds": [1, 2, 3], "seed": 99})
        assert orr._provenance({"kind": "tone", "bin_offset": 0.3, "seed": 1}) == {
            "bin_offset": 0.3, "seeds": [1]}

    def test_sweep_specs_raise_when_a_kind_geometry_disagrees(self):
        original = dict(vectors.VECTOR_SETS)
        vectors.VECTOR_SETS["tone90"] = dict(original["tone90"], bin_offset=0.25)
        try:
            try:
                vectors.sweep_specs()
            except ValueError as e:
                assert "tone" in str(e) and "bin_offset" in str(e), e
            else:
                assert False, "sweep_specs did not raise on disagreeing tone bin_offset"
        finally:
            vectors.VECTOR_SETS.clear()
            vectors.VECTOR_SETS.update(original)
