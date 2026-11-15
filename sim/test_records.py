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
from pathlib import Path

from sim import records

VERIFICATION = Path(__file__).resolve().parent.parent / "verification"
sys.path.append(str(VERIFICATION))
import test_fft256_smoke  # noqa: E402  (its `flow_tools` import lives there)


def test_append_only_earlier_record_unchanged():
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


def test_file_format_is_canonical_indent2_with_trailing_newline():
    """`json.dumps(..., indent=2) + "\\n"` byte-for-byte: a re-indent would
    rewrite every committed evidence file wholesale on its next append, which
    is exactly the failure this consolidation guards against."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        records.append_record(path, {"b": 1, "a": [1, 2]})
        text = path.read_text()
    assert text == json.dumps(json.loads(text), indent=2) + "\n"


def test_missing_file_starts_empty_and_rec_is_returned():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        rec = records.append_record(path, {"n": 1})
        assert rec == {"n": 1}, rec
        assert json.loads(path.read_text()) == {"records": [{"n": 1}]}


def test_utc_stamp_format():
    stamp = records.utc_stamp()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp), stamp
    datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")


def test_parse_record_argv_shapes():
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


def test_smoke_writer_delegates_with_record_as_default_path():
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


def test_json_safe_encodes_non_finite_per_the_evidence_convention():
    """`measurements/README.md`'s convention, implemented here: an exact SQNR
    match is the string `"inf"`, any other non-finite value is `null` --
    strict JSON cannot carry a non-finite number, and `json.dumps` would emit
    a bare `Infinity`/`NaN` literal that strict readers reject."""
    assert records.json_safe(float("inf")) == "inf"
    assert records.json_safe(float("-inf")) == "-inf"
    assert records.json_safe(float("nan")) is None


def test_json_safe_rounds_to_four_decimals_by_default():
    """The rounding is explicit, not silent: `ndigits` defaults to the four
    decimals every committed record's figures carry (`schedule-sweep.json`,
    `model-sizes.json`), matching `fixedpoint_model.score_set`'s `ndigits`
    parameter; a caller wanting unrounded values passes `ndigits=None`."""
    assert records.json_safe(70.729749) == 70.7297
    assert records.json_safe(59.66476) == 59.6648
    assert records.json_safe(1234.5) == 1234.5
    assert records.json_safe(70.729749, ndigits=None) == 70.729749


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
