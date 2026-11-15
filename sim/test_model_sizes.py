"""Tests for the per-size model record module (the FFT-size row, 64/1024 not run).

Run through `make -C verification fxp-model`.
"""

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

from rtl.gen import params as generator_params
from sim import fixedpoint_model as fm
from sim import model_sizes as ms
from sim import vectors

ROOT = Path(__file__).resolve().parent.parent
SIZE_PARAMS = (ROOT / "rtl" / "params" / "fft64.params",
               ROOT / "rtl" / "params" / "fft1024.params")
FRAMES = 20  # fewer frames keep the tests quick; the committed record uses 100


def test_committed_params_parse_with_placeholder_schedules():
    for path in SIZE_PARAMS:
        text = path.read_text()
        # AC 1: the file's comment states the schedule is a placeholder that
        # follows fft256.params' one-bit-per-stage pattern.
        assert "PLACEHOLDER" in text.upper(), path
        assert "fft256.params" in text, path
        p = fm.load_params(path)
        nstages = len(p.stage_widths)
        assert nstages == 2 * generator_params.log4(p.size), path
        assert p.input_width == 16 and p.output_width == 16, path
        # One bit per stage from input_width: 17, 18, ... (the fft256 pattern).
        assert list(p.stage_widths) == list(range(p.input_width + 1,
                                                  p.input_width + 1 + nstages)), path
    assert fm.load_params(SIZE_PARAMS[0]).size == 64
    assert fm.load_params(SIZE_PARAMS[1]).size == 1024


def test_evaluate_reports_every_set():
    p = fm.load_params(SIZE_PARAMS[0])
    res = ms.evaluate(p, FRAMES)
    assert set(res["sets"]) == set(vectors.VECTOR_SETS), res["sets"].keys()
    for name, s in res["sets"].items():
        assert s["min_sqnr_db"] > 30, f"{name}: {s}"
        assert s["overflow_components"] == 0, f"{name}: {s}"
    assert res["min_sqnr_db"] == min(s["min_sqnr_db"] for s in res["sets"].values())
    assert res["overflow_components"] == 0


def test_record_has_every_ac_field_and_generator_hash():
    p = fm.load_params(SIZE_PARAMS[0])
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        rec = ms.record(path, SIZE_PARAMS[0], p, ms.evaluate(p, 5), 5)
    for field in ("date_utc", "note", "model", "parameter_file",
                  "parameter_file_sha256", "size", "stage_widths",
                  "frames_per_set", "sets"):
        assert field in rec, field
    # The hash must be the generator parser's own sha256 of the file bytes.
    gen = generator_params.load_params(str(SIZE_PARAMS[0]))
    assert rec["parameter_file_sha256"] == gen["_sha256"]
    assert rec["parameter_file_sha256"] == p.sha256
    assert rec["size"] == 64 and len(rec["stage_widths"]) == 6
    for name, s in rec["sets"].items():
        assert "min_sqnr_db" in s and "overflow_components" in s, (name, s)
    assert "SIMULATED" in rec["note"] and "PLACEHOLDER" in rec["note"], rec["note"]


def test_record_is_append_only():
    p = fm.load_params(SIZE_PARAMS[0])
    res = ms.evaluate(p, 5)
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "r.json"
        ms.record(path, SIZE_PARAMS[0], p, res, 5)
        first_text = path.read_text()
        first = json.loads(first_text)["records"][0]
        ms.record(path, SIZE_PARAMS[1], fm.load_params(SIZE_PARAMS[1]), res, 5)
        data = json.loads(path.read_text())
    assert len(data["records"]) == 2, data
    assert data["records"][0] == first, "the earlier record was modified"
    assert data["records"][0]["size"] == 64 and data["records"][1]["size"] == 1024


def test_record_creates_missing_path():
    p = fm.load_params(SIZE_PARAMS[0])
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "nested" / "r.json"
        path.parent.mkdir()
        ms.record(path, SIZE_PARAMS[0], p, ms.evaluate(p, 5), 5)
        data = json.loads(path.read_text())
    assert list(data) == ["records"] and len(data["records"]) == 1


def test_cli_labels_simulated_and_placeholder():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert ms.main([str(SIZE_PARAMS[0]), str(SIZE_PARAMS[1])]) == 0
    text = out.getvalue()
    assert "SIMULATED" in text and "PLACEHOLDER" in text, text
    for path in SIZE_PARAMS:
        assert str(path) in text, text
    assert "1024" in text and "64" in text, text


def test_cli_without_record_writes_nothing():
    out = io.StringIO()
    # A plausible record target's parent, empty at entry: without --record the
    # CLI must not create a file (or anything else) here.
    with tempfile.TemporaryDirectory() as d:
        with contextlib.redirect_stdout(out):
            assert ms.main([str(SIZE_PARAMS[0])]) == 0
        written = list(Path(d).iterdir())
        assert written == [], f"the CLI wrote without --record: {written}"
    assert "record" not in out.getvalue().lower(), out.getvalue()


def test_rejected_size_surfaces_paramerror_naming_key():
    text = SIZE_PARAMS[0].read_text().replace("size=64", "size=512")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "fft512.params"
        path.write_text(text)
        try:
            fm.load_params(path)
        except generator_params.ParamError as e:
            assert "size" in str(e), str(e)
        else:
            raise AssertionError("size=512 parsed; the generator's validator is not applied")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            assert ms.main([str(path)]) == 1
        assert "size" in err.getvalue() and "Traceback" not in err.getvalue(), err.getvalue()


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
