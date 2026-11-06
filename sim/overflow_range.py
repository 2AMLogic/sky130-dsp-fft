"""Measured-by-simulation no-overflow amplitude range of the fixed-point model.

For each vector kind the amplitude fraction is stepped from FRACTION_LO to
FRACTION_HI and the model is run on FRAMES frames per step. A step "overflows"
if any stage (or the output) counts one or more overflow components. All
figures are SIMULATED (this model, not silicon) and on the PLACEHOLDER
schedule (spec, Internal growth row): they say nothing about a final schedule.

Overflow need not be monotone in amplitude, so the reported range is the
largest fraction below the FIRST overflowing step; a later clean step above
an overflowing one is ignored. If no step overflows the range is reported as
">= FRACTION_HI"; if the first step overflows, "< FRACTION_LO".

CLI, from the repo root:
    python3 -m sim.overflow_range <params-file> [--record measurements/overflow-range.json]
`--record` appends one dated record to the file (append-only evidence).
"""

import datetime
import json

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fixedpoint_model as fm  # noqa: E402
import vectors  # noqa: E402

FRACTION_LO = 0.50
FRACTION_HI = 1.00
STEP = 0.01
FRAMES = 100

# Seeds are those of the fixed sets: random uses random50 + random70 seeds
# (1..20, frames split evenly), tone uses the tone sets' seed and bin offset.
KINDS = {
    "random": {"kind": "random", "seeds": list(range(1, 21))},
    "tone": {"kind": "tone", "bin_offset": 0.3, "seed": 1},
}


def fractions():
    steps = round((FRACTION_HI - FRACTION_LO) / STEP)
    return [round(FRACTION_LO + i * STEP, 2) for i in range(steps + 1)]


def _stage_label(i, nstages):
    return "output" if i == nstages else f"stage {i}"


def sweep_kind(params: fm.Params, spec: dict, frames: int = FRAMES) -> dict:
    """Sweep one kind; returns max no-overflow fraction and the first overflowing stage."""
    nstages = len(params.stage_widths)
    last_clean = None
    for f in fractions():
        data = vectors.generate_swept_frames(
            spec, f, n=params.size, width=params.input_width, frames=frames)
        model = fm.FixedPointFFT(params)
        model.run(data.real.astype("int64"), data.imag.astype("int64"))
        bad = [i for i, c in enumerate(model.stats.overflow) if c]
        if bad:
            return {
                "max_no_overflow_fraction": last_clean,
                "first_overflow_fraction": f,
                "first_overflow_stage": _stage_label(bad[0], nstages),
                "bound": "exact" if last_clean is not None else "below_sweep_start",
            }
        last_clean = f
    return {
        "max_no_overflow_fraction": last_clean,
        "first_overflow_fraction": None,
        "first_overflow_stage": None,
        "bound": "at_least_sweep_end",
    }


def sweep(params: fm.Params, frames: int = FRAMES) -> dict:
    return {name: sweep_kind(params, spec, frames) for name, spec in KINDS.items()}


def describe(r: dict) -> str:
    m = r["max_no_overflow_fraction"]
    if r["bound"] == "at_least_sweep_end":
        return f">= {FRACTION_HI:.2f} (no overflow anywhere in the sweep)"
    if m is None:
        return (f"< {FRACTION_LO:.2f} (overflows at {r['first_overflow_fraction']:.2f}, "
                f"first in {r['first_overflow_stage']})")
    return (f"{m:.2f} (first overflow at {r['first_overflow_fraction']:.2f}, "
            f"first in {r['first_overflow_stage']})")


def record(path, params_file, p: fm.Params, res: dict) -> dict:
    """Append one dated record to `path` ({"records": [...]}); earlier records are kept."""
    rec = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "SIMULATED (model, not silicon) and on the PLACEHOLDER schedule "
                "(spec, Internal growth row); no final-schedule or timing claim",
        "model": fm.MODEL_ID,
        "parameter_file": str(params_file),
        "parameter_file_sha256": p.sha256,
        "stage_widths": list(p.stage_widths),
        "sweep": {"fraction_lo": FRACTION_LO, "fraction_hi": FRACTION_HI, "step": STEP,
                  "frames_per_step": FRAMES,
                  "rule": "largest fraction below the first overflowing step"},
        "kinds": {name: dict(r, seeds=(KINDS[name]["seeds"] if "seeds" in KINDS[name]
                                       else [KINDS[name]["seed"]]),
                             **({"bin_offset": KINDS[name]["bin_offset"]}
                                if "bin_offset" in KINDS[name] else {}))
                  for name, r in res.items()},
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
        print("usage: python3 -m sim.overflow_range <params-file> [--record <json>]",
              file=sys.stderr)
        return 2
    p = fm.load_params(argv[0])
    res = sweep(p)
    print(f"model:   {fm.MODEL_ID}")
    print(f"params:  {argv[0]} sha256={p.sha256}")
    print(f"sweep:   fraction {FRACTION_LO:.2f}..{FRACTION_HI:.2f} step {STEP}, {FRAMES} frames/step")
    print("No-overflow amplitude range (SIMULATED, on the PLACEHOLDER schedule; "
          "largest fraction below the first overflowing step):")
    for name, r in res.items():
        print(f"  {name:7s} {describe(r)}")
    if rec_path:
        record(rec_path, argv[0], p, res)
        print(f"record appended to {rec_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
