"""Recorded model runs for the FFT-size row's fallback and stretch sizes.

`spec/spec.md`'s FFT-size row names a 64-point fallback and a 1024-point
stretch with the verification method "`sim/` model run per size", and its
status cell reads "64/1024 not run". This module runs the bit-accurate model
on the spec's SQNR vector sets (`vectors.VECTOR_SETS`) for each parameter file
given and appends one dated record per file, so the row's model-run half is
evidence at generator-legal sizes. (The row's other half, RTL bit-exact vs.
model, needs generated RTL at each size and is not produced here.)

The `stage_widths` in `rtl/params/fft64.params` and `rtl/params/fft1024.params`
are PLACEHOLDERS following `rtl/params/fft256.params`' one-bit-per-stage
pattern: every figure this module records carries no accuracy claim, and no
schedule is selected here -- choosing a schedule for any size is a decision
record's job. Ten radix-2 stages accumulate more rounding noise than eight,
so the 1024-point figures on the 16-bit placeholder land below the spec's
60 dB SQNR target row. That is an artifact of pairing a stretch SIZE with the
target WIDTH, not a verdict on 1024-point feasibility. Record the figure; do
not widen a schedule to clear a bar.

Per-set scoring is `fixedpoint_model.score_set`, so this module and the
candidate-growth survey share one measurement path.

CLI, from the repo root:
    python3 -m sim.model_sizes <params-file>... [--record measurements/model-sizes.json]
`--record` appends one dated record per parameter file (append-only evidence).
"""

import math
import sys

from rtl.gen import params as generator_params
from sim import fixedpoint_model as fm
from sim import records
from sim import vectors

FRAMES = vectors.FRAMES_PER_SET


def evaluate(p: fm.Params, frames: int = FRAMES) -> dict:
    """Score one parameter file on every vector set; per-set minimum SQNR and overflow."""
    model = fm.FixedPointFFT(p)
    sets = {}
    for name in vectors.VECTOR_SETS:
        data = vectors.generate_frames(name, n=p.size, width=p.input_width, frames=frames)
        sets[name] = fm.score_set(model, data)
    worst = min(s["min_sqnr_db"] for s in sets.values())
    return {"sets": sets,
            "min_sqnr_db": worst,
            "overflow_components": sum(s["overflow_components"] for s in sets.values())}


def _db(x: float) -> str:
    return "    inf" if math.isinf(x) else f"{x:7.2f}"


def describe(res: dict) -> str:
    """Per-set report lines for one parameter file, in `vectors.VECTOR_SETS`
    order, with the `worst-set min` summary line last."""
    lines = [f"  {name:9s} min {_db(s['min_sqnr_db'])} dB  "
             f"ovf {s['overflow_components']}" for name, s in res["sets"].items()]
    lines.append(f"  worst-set min {_db(res['min_sqnr_db'])} dB")
    return "\n".join(lines)


def record(path, params_file, p: fm.Params, res: dict, frames: int = FRAMES) -> dict:
    """Append one dated record to `path` ({"records": [...]}); earlier records are kept."""
    rec = {
        "date_utc": records.utc_stamp(),
        "note": "SIMULATED (this model against a double-precision reference, not "
                "silicon) and on the PLACEHOLDER schedule: this size's stage_widths "
                "follow rtl/params/fft256.params' one-bit-per-stage pattern and "
                "carry no accuracy claim. No schedule is selected; a schedule for "
                "any size is a decision record's job.",
        "model": fm.MODEL_ID,
        "parameter_file": str(params_file),
        "parameter_file_sha256": p.sha256,
        "size": p.size,
        "stage_widths": list(p.stage_widths),
        "twiddle_width": p.twiddle_width,
        "frames_per_set": frames,
        "vector_sets": list(vectors.VECTOR_SETS),
        "sqnr_encoding": "numbers in dB; an exact match is the string \"inf\", "
                         "any other non-finite value is null (strict JSON cannot "
                         "carry a non-finite number)",
        "reading_note": "the 1024-point figures on the 16-bit placeholder land "
                        "below the spec's 60 dB SQNR target row because ten "
                        "radix-2 stages accumulate more rounding noise than "
                        "eight: an artifact of pairing a stretch size with the "
                        "target width, not a verdict on 1024-point feasibility "
                        "(the stretch row's own 18-bit width is decision 0002's "
                        "to study). Record the figure; do not widen a schedule "
                        "to clear a bar.",
        "sets": {name: {"min_sqnr_db": records.json_safe(s["min_sqnr_db"]),
                        "overflow_components": s["overflow_components"]}
                 for name, s in res["sets"].items()},
        "min_sqnr_db": records.json_safe(res["min_sqnr_db"]),
        "overflow_components": res["overflow_components"],
    }
    return records.append_record(path, rec)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rec_path = None
    if "--record" in argv:
        i = argv.index("--record")
        if i == 0 or i != len(argv) - 2:
            print("usage: python3 -m sim.model_sizes <params-file>... "
                  "[--record <json>]", file=sys.stderr)
            return 2
        rec_path, argv = argv[i + 1], argv[:i]
    if not argv:
        print("usage: python3 -m sim.model_sizes <params-file>... "
              "[--record <json>]", file=sys.stderr)
        return 2
    print(f"model:   {fm.MODEL_ID}")
    print(f"sizes:   {len(argv)} parameter file(s) x {len(vectors.VECTOR_SETS)} "
          f"vector sets x {FRAMES} frames/set")
    print("SIMULATED figures on the PLACEHOLDER schedule (fft256.params' "
          "one-bit-per-stage pattern); no accuracy claim, no schedule selected.")
    status = 0
    for f in argv:
        try:
            p = fm.load_params(f)
        except generator_params.ParamError as e:
            print(f"error: {f}: {e}", file=sys.stderr)
            status = 1
            continue
        res = evaluate(p)
        print(f"{f}  sha256={p.sha256}  size={p.size}")
        print(describe(res))
        if rec_path:
            record(rec_path, f, p, res, FRAMES)
    if rec_path and status == 0:
        print(f"records appended to {rec_path}")
    return status


if __name__ == "__main__":
    sys.exit(main())
