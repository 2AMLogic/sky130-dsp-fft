"""Candidate growth schedules for the 256-point FFT, scored by the bit-accurate model.

`spec/spec.md`'s "Internal growth and scaling" row is an open target: the
`stage_widths` and `twiddle_width` in `rtl/params/fft256.params` are
PLACEHOLDERS, and every simulated SQNR figure on main rests on them. This
module runs `fixedpoint_model` over the CANDIDATES table on the spec's SQNR
vector sets (`vectors.VECTOR_SETS`) and reports, per candidate, the per-set
minimum SQNR, the per-set overflow component count and the sum of stage widths
as a size proxy.

Every figure here is SIMULATED (this model against a double-precision
reference), never measured on silicon. This module REPORTS; it selects
nothing. Choosing a schedule, and editing the parameter file or the spec, is a
decision record's job.

Two findings the table makes visible, both reproducible by running it:

* Minimum SQNR is NOT monotone in the sum of stage widths. `front-loaded
  growth` has the largest width sum and the worst accuracy (it is the only
  candidate below the spec's SQNR target); the shape of the schedule dominates
  its total. A reader ranking candidates by width sum would rank them wrongly.
* The overflow column reads 0 for every candidate. Overflow in this model is
  amplitude driven, not width driven: each stage performs exactly one reduction
  dropping `max(0, (stage_widths[i-1] + 1) - stage_widths[i])` LSBs, so a
  narrow stage is scale-compensated and a wide one only sign-extends (the same
  mechanism `overflow_range.py` and its tests record). The amplitude at which
  the placeholder does overflow is `overflow_range.py`'s question, not this
  module's; `test_schedule_sweep.py` uses it as the control that proves this
  column is wired to the model's `Stats` rather than hard-coded.

Candidates are built by overriding `stage_widths` / `twiddle_width` on the base
parameter file's `Params`; no parameter file is written, so the recorded
`parameter_file_sha256` names the BASE file and never a candidate. Each
candidate is round-tripped through the generator's own parser
(`rtl/gen/params.py`) and the verdict recorded, because a candidate the
generator rejects could not become RTL.

CLI, from the repo root:
    python3 -m sim.schedule_sweep <params-file> [--record measurements/schedule-sweep.json]
`--record` appends one dated record to the file (append-only evidence).
"""

import datetime
import json
import math
import sys
from pathlib import Path

from rtl.gen import params as generator_params
from sim import fixedpoint_model as fm
from sim import reference, vectors

FRAMES = vectors.FRAMES_PER_SET

# spec/spec.md, SQNR row: >= 60 dB at 16-bit output is the ratified target for
# the 256-point configuration. Reported per candidate as context; this module
# does not select, reject or rank on it.
SPEC_SQNR_TARGET_DB = 60.0

# The study: what varies is `stage_widths` and `twiddle_width`; every other key
# comes from the base parameter file. `note` records why each row is here.
# AC 3: the current placeholder is present, and rows 2-6 all grow by less than
# one bit per stage.
CANDIDATES = (
    {"name": "placeholder (1 bit/stage)",
     "stage_widths": (17, 18, 19, 20, 21, 22, 23, 24), "twiddle_width": 16,
     "note": "the committed placeholder; the baseline every figure on main rests on"},
    {"name": "0002 reference point",
     "stage_widths": (17, 18, 18, 19, 19, 20, 20, 21), "twiddle_width": 16,
     "note": "+1 bit at the first stage then 1 per two stages, 21-bit core output; "
             "spec/decisions/0002 carries this as a reference point from the "
             "superseded dblclockfft candidate, not as a property of the chosen generator"},
    {"name": "0002 reference point, tw=14",
     "stage_widths": (17, 18, 18, 19, 19, 20, 20, 21), "twiddle_width": 14,
     "note": "same schedule with a cheaper twiddle, to separate the two axes"},
    {"name": "half bit/stage",
     "stage_widths": (17, 17, 18, 18, 19, 19, 20, 20), "twiddle_width": 16,
     "note": "growth every second stage from input_width+1"},
    {"name": "flat at input+1",
     "stage_widths": (17, 17, 17, 17, 17, 17, 17, 17), "twiddle_width": 16,
     "note": "one guard bit, no growth"},
    {"name": "zero growth",
     "stage_widths": (16, 16, 16, 16, 16, 16, 16, 16), "twiddle_width": 16,
     "note": "the narrowest generator-legal schedule for a 16-bit input"},
    {"name": "front-loaded growth",
     "stage_widths": (18, 20, 21, 22, 22, 22, 22, 22), "twiddle_width": 16,
     "note": "widest total; included because it shows minimum SQNR is not "
             "monotone in the width sum"},
    {"name": "placeholder, tw=12",
     "stage_widths": (17, 18, 19, 20, 21, 22, 23, 24), "twiddle_width": 12,
     "note": "twiddle axis below the knee, placeholder schedule held fixed"},
    {"name": "placeholder, tw=20",
     "stage_widths": (17, 18, 19, 20, 21, 22, 23, 24), "twiddle_width": 20,
     "note": "twiddle axis above the knee, placeholder schedule held fixed"},
)


def candidate_params(base: fm.Params, cand: dict) -> fm.Params:
    """The base parameters with this candidate's widths substituted.

    `sha256` is inherited from the base file and is therefore the BASE file's
    hash, not a hash of this configuration -- no file holds it. `record` names
    it once for the base file and never per candidate.
    """
    return fm.Params(**dict(base.__dict__,
                            stage_widths=tuple(cand["stage_widths"]),
                            twiddle_width=cand["twiddle_width"]))


def _render_params(p: fm.Params) -> str:
    """A parameter-file text for `p`, for validation only (never written to disk)."""
    return "".join(f"{k}={v}\n" for k, v in (
        ("size", p.size),
        ("architecture", p.architecture),
        ("direction", p.direction),
        ("output_order", p.output_order),
        ("input_width", p.input_width),
        ("output_width", p.output_width),
        ("stage_widths", ",".join(str(w) for w in p.stage_widths)),
        ("twiddle_width", p.twiddle_width),
        ("complex_mult", p.complex_mult),
        ("rounding", p.rounding),
        ("pipeline", p.pipeline),
        ("stall", p.stall),
    ))


def generator_verdict(p: fm.Params):
    """(legal, reason) from the generator's own validator; reason is None when legal.

    A candidate the generator rejects cannot become RTL, so studying it would
    produce an unselectable answer. The verdict is recorded, not enforced.
    """
    try:
        generator_params.parse_params(_render_params(p))
    except generator_params.ParamError as e:
        return False, str(e)
    return True, None


def score_frames(model: fm.FixedPointFFT, data) -> dict:
    """One set's figures for `model`: minimum simulated SQNR and overflow count.

    `Stats` accumulates, so it is reset first: AC 2 asks for a per-set overflow
    count and a shared model would otherwise report a running total. This is
    the whole measurement path, so the overflow negative control in
    `test_schedule_sweep.py` drives it with full-scale frames rather than
    re-implementing it.
    """
    model.stats = fm.Stats(len(model.p.stage_widths))
    return {"min_sqnr_db": reference.set_sqnr_db(data, model.candidate),
            "overflow_components": sum(model.stats.overflow)}


def evaluate(base: fm.Params, cand: dict, frames: int = FRAMES) -> dict:
    """Score one candidate on every vector set; per-set minimum SQNR and overflow."""
    p = candidate_params(base, cand)
    legal, reason = generator_verdict(p)
    model = fm.FixedPointFFT(p)
    sets = {}
    for name in vectors.VECTOR_SETS:
        data = vectors.generate_frames(name, n=p.size, width=p.input_width, frames=frames)
        sets[name] = score_frames(model, data)
    worst = min(s["min_sqnr_db"] for s in sets.values())
    return {
        "name": cand["name"],
        "note": cand["note"],
        "stage_widths": list(p.stage_widths),
        "twiddle_width": p.twiddle_width,
        "width_sum": sum(p.stage_widths),
        "generator_legal": legal,
        "generator_error": reason,
        "sets": sets,
        "min_sqnr_db": worst,
        "overflow_components": sum(s["overflow_components"] for s in sets.values()),
        # +inf (an exact match) clears the target like any larger figure would.
        "meets_spec_sqnr_target": worst >= SPEC_SQNR_TARGET_DB,
    }


def sweep(base: fm.Params, candidates=CANDIDATES, frames: int = FRAMES) -> list:
    """Evaluate every candidate; returns one result dict per candidate, in order."""
    return [evaluate(base, c, frames) for c in candidates]


def describe(r: dict) -> str:
    """One table row: widths, size proxy, worst-set SQNR, overflow, verdicts."""
    sq = r["min_sqnr_db"]
    sq_txt = "    inf" if math.isinf(sq) else f"{sq:7.2f}"
    return (f"  {r['name']:28s} {','.join(str(w) for w in r['stage_widths']):23s} "
            f"tw={r['twiddle_width']:<3d} sum={r['width_sum']:<4d} "
            f"min {sq_txt} dB  ovf {r['overflow_components']:<4d} "
            f"{'legal' if r['generator_legal'] else 'ILLEGAL':7s} "
            f"{'pass' if r['meets_spec_sqnr_target'] else 'FAIL'}")


def _json_safe(x: float):
    """Strict JSON has no `Infinity`/`NaN` literal, and `json.dumps` emits them anyway.

    An exact match (`reference.sqnr_db` returns +inf) becomes the string
    `"inf"`; any other non-finite value becomes `null`. Stated in
    `measurements/README.md` so a reader of the record knows the convention.
    """
    if math.isinf(x):
        return "inf" if x > 0 else "-inf"
    if math.isnan(x):
        return None
    return round(float(x), 4)


def record(path, params_file, base: fm.Params, results: list, frames: int = FRAMES) -> dict:
    """Append one dated record to `path` ({"records": [...]}); earlier records are kept."""
    rec = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "SIMULATED (this model against a double-precision reference, not "
                "silicon). A survey of candidate growth schedules for the spec's "
                "Internal growth row: it reports, it selects nothing. No schedule "
                "is chosen and no timing or area claim is made here.",
        "model": fm.MODEL_ID,
        "parameter_file": str(params_file),
        "parameter_file_sha256": base.sha256,
        "base_note": "the sha256 is the BASE parameter file's. Each candidate "
                     "overrides stage_widths and twiddle_width only; no parameter "
                     "file holds a candidate, so no candidate has a hash of its own.",
        "frames_per_set": frames,
        "vector_sets": list(vectors.VECTOR_SETS),
        "spec_sqnr_target_db": SPEC_SQNR_TARGET_DB,
        "sqnr_encoding": "numbers in dB; an exact match is the string \"inf\", "
                         "any other non-finite value is null (strict JSON cannot "
                         "carry a non-finite number)",
        "candidates": [{
            "name": r["name"],
            "note": r["note"],
            "stage_widths": r["stage_widths"],
            "twiddle_width": r["twiddle_width"],
            "width_sum": r["width_sum"],
            "generator_legal": r["generator_legal"],
            "generator_error": r["generator_error"],
            "meets_spec_sqnr_target": r["meets_spec_sqnr_target"],
            "sets": {name: {"min_sqnr_db": _json_safe(s["min_sqnr_db"]),
                            "overflow_components": s["overflow_components"]}
                     for name, s in r["sets"].items()},
        } for r in results],
    }
    path = Path(path)
    data = json.loads(path.read_text()) if path.exists() else {"records": []}
    data["records"].append(rec)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return rec


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rec_path = None
    if len(argv) == 3 and argv[1] == "--record":
        argv, rec_path = argv[:1], argv[2]
    if len(argv) != 1:
        print("usage: python3 -m sim.schedule_sweep <params-file> [--record <json>]",
              file=sys.stderr)
        return 2
    base = fm.load_params(argv[0])
    results = sweep(base, CANDIDATES, FRAMES)
    print(f"model:   {fm.MODEL_ID}")
    print(f"params:  {argv[0]} sha256={base.sha256}  (BASE file; each candidate "
          f"overrides stage_widths/twiddle_width only)")
    print(f"sweep:   {len(CANDIDATES)} candidates x {len(vectors.VECTOR_SETS)} vector sets "
          f"x {FRAMES} frames/set")
    print(f"Candidate growth schedules (SIMULATED, never measured; min SQNR is the worst "
          f"vector set; 'pass' is >= {SPEC_SQNR_TARGET_DB:.0f} dB, the spec's SQNR target).")
    print("This table REPORTS; no schedule is selected here. Minimum SQNR is not "
          "monotone in the width sum, so do not rank by `sum`.")
    for r in results:
        print(describe(r))
    print("Overflow is 0 for every candidate: in this model overflow is amplitude "
          "driven, not width driven (see the module docstring and overflow_range.py).")
    if rec_path:
        record(rec_path, argv[0], base, results, FRAMES)
        print(f"record appended to {rec_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
