"""Tests for the one append-only evidence writer (`sim/records.py`).

Run through `make -C verification fxp-model`.

The invariant under test is the repo's evidence rule (`measurements/README.md`,
"Never edit or drop an earlier record"; `CLAUDE.md`: recorded results are
append-only evidence). It is asserted here once, at full strength -- the
earlier record must be unchanged after a later append, not merely still
counted -- and it covers all three writers that produce the committed evidence
files, including `verification/test_fft256_smoke.py`'s, which had no path
parameter and no test before this consolidation.
"""

import datetime
import inspect
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from sim import records, reference

VERIFICATION = Path(__file__).resolve().parent.parent / "verification"
sys.path.append(str(VERIFICATION))
import test_fft256_smoke  # noqa: E402  (its `flow_tools` import lives there)


class _ScoreStubModel:
    """The bare attribute shape `fixedpoint_model.score_set` needs:
    `p.stage_widths` for the `Stats` reset, a settable `stats`, and a
    `candidate` (`None` where the scorer itself is stubbed, the
    double-precision reference where the exact-match path is driven for
    real)."""

    class p:
        stage_widths = (8, 8)

    def __init__(self, candidate=None):
        self.stats = None
        self.candidate = candidate


class Records(unittest.TestCase):
    def test_append_only_earlier_record_unchanged(self):
        """The real invariant, at the strength `test_schedule_sweep.py` held before
        the consolidation: the earlier record is not merely still present but
        identical -- a copy that rewrote record 0 in place, or capped the file at
        the N most recent records, fails this."""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            records.append_record(path, {"n": 1, "payload": {"a": [1, 2, 3]}})
            records.append_record(path, {"n": 2})
            data = json.loads(path.read_text())
        assert len(data["records"]) == 2, data
        assert data["records"][0] == {"n": 1, "payload": {"a": [1, 2, 3]}}, \
            "the earlier record was modified"

    def test_file_format_is_canonical_indent2_with_trailing_newline(self):
        """`json.dumps(..., indent=2) + "\\n"` byte-for-byte: a re-indent would
        rewrite every committed evidence file wholesale on its next append, which
        is exactly the failure this consolidation guards against."""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            records.append_record(path, {"b": 1, "a": [1, 2]})
            text = path.read_text()
        assert text == json.dumps(json.loads(text), indent=2) + "\n"

    def test_missing_file_starts_empty_and_rec_is_returned(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            rec = records.append_record(path, {"n": 1})
            assert rec == {"n": 1}, rec
            assert json.loads(path.read_text()) == {"records": [{"n": 1}]}

    def test_utc_stamp_format(self):
        stamp = records.utc_stamp()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp), stamp
        datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")

    def test_parse_record_argv_shapes(self):
        usage = "usage: python3 -m sim.<module> <params-file> [--record <json>]"
        assert records.parse_record_argv(["p"], usage) == (["p"], None)
        assert records.parse_record_argv(["p", "--record", "r.json"], usage) == \
            (["p"], "r.json")
        for bad in ([], ["p", "q"], ["p", "--record"], ["p", "--record", "a", "b"],
                    ["--record", "r"]):
            try:
                records.parse_record_argv(bad, usage)
            except ValueError as e:
                assert usage in str(e), f"argv {bad}: wrong error {e}"
            else:
                raise AssertionError(f"argv {bad} was accepted")

    def test_smoke_writer_delegates_with_record_as_default_path(self):
        """The writer feeding `measurements/fft256-smoke.json` is covered too: it
        takes a path now (so it is testable against a tmp file), defaults to the
        module's RECORD constant, and behaves exactly like the helper."""
        sig = inspect.signature(test_fft256_smoke.append_record)
        assert list(sig.parameters) == ["record", "path"], sig
        assert sig.parameters["path"].default is test_fft256_smoke.RECORD
        assert test_fft256_smoke.RECORD.name == "fft256-smoke.json"
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            test_fft256_smoke.append_record({"n": 1, "payload": ["x"]}, path=path)
            test_fft256_smoke.append_record({"n": 2}, path=path)
            text = path.read_text()
        data = json.loads(text)
        assert [r["n"] for r in data["records"]] == [1, 2], data
        assert data["records"][0] == {"n": 1, "payload": ["x"]}, \
            "the earlier record was modified"
        assert text == json.dumps(data, indent=2) + "\n"

    def test_json_safe_encodes_non_finite_per_the_evidence_convention(self):
        """`measurements/README.md`'s convention, implemented here: an exact SQNR
        match is the string `"inf"`, any other non-finite value is `null` --
        strict JSON cannot carry a non-finite number, and `json.dumps` would emit
        a bare `Infinity`/`NaN` literal that strict readers reject."""
        assert records.json_safe(float("inf")) == "inf"
        assert records.json_safe(float("-inf")) is None
        assert records.json_safe(float("nan")) is None

    def test_json_safe_rounds_to_four_decimals_by_default(self):
        """The rounding is explicit, not silent: `ndigits` defaults to the four
        decimals every committed record's figures carry (`schedule-sweep.json`,
        `model-sizes.json`), matching `fixedpoint_model.score_set`'s `ndigits`
        parameter; a caller wanting unrounded values passes `ndigits=None`."""
        assert records.json_safe(70.729749) == 70.7297
        assert records.json_safe(59.66476) == 59.6648
        assert records.json_safe(1234.5) == 1234.5
        assert records.json_safe(70.729749, ndigits=None) == 70.729749

    def test_smoke_sqnr_exact_match_is_the_string_inf_and_strictly_serialisable(self):
        """The smoke record's SQNR field must not bypass the shared encoder: on
        the exact-match path `score_set` returns a bare +inf (`reference.sqnr_db`
        on equal outputs), which `json.dumps` would emit as a bare `Infinity`
        literal -- invalid strict JSON, appended permanently to evidence. A stub
        model whose `candidate` *is* the double-precision reference drives that
        path; the recorded figure is the string `"inf"` and the record is
        strictly serialisable."""
        model = _ScoreStubModel(candidate=reference.reference_fft)
        frames = np.array([[1 + 0j, 2 + 2j, 3 - 1j, 0 + 4j]])
        out = test_fft256_smoke.simulated_sqnr(model, {"exact": frames})
        assert out["exact"]["min_sqnr_db"] == "inf", out
        assert out["exact"]["overflow_components"] == 0, out
        json.dumps(out, allow_nan=False)  # raises on any bare non-finite float

    def test_append_record_rejects_non_finite_and_leaves_the_file_unchanged(self):
        """The shared writer serialises with `allow_nan=False`: a record still
        carrying a bare non-finite float raises `ValueError` before the file is
        written -- a failed append must never truncate or rewrite the evidence
        already in the file."""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "r.json"
            records.append_record(path, {"n": 1})
            before = path.read_text()
            for bad in (float("inf"), float("-inf"), float("nan")):
                try:
                    records.append_record(path, {"sqnr_db": bad})
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"non-finite {bad!r} was written")
            assert path.read_text() == before, "the failed append modified the file"

    def test_smoke_sqnr_finite_path_keeps_two_decimals(self):
        """Format-drift guard: routing the smoke record's SQNR through
        `json_safe` without `ndigits=2` silently widens the figure from the
        record's 2 decimals to the encoder default of 4 inside append-only
        evidence. The scorer is stubbed to a figure whose 2- and 4-decimal
        roundings differ, so only the correctly parameterised call records
        65.65."""
        model = _ScoreStubModel()
        frames = np.zeros((1, 4), dtype=np.complex128)
        real_scorer = reference.set_sqnr_db
        reference.set_sqnr_db = lambda frames, candidate: 65.654999
        try:
            out = test_fft256_smoke.simulated_sqnr(model, {"fmt": frames})
        finally:
            reference.set_sqnr_db = real_scorer
        assert out["fmt"]["min_sqnr_db"] == 65.65, out
