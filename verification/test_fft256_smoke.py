"""End-to-end smoke of the generated 256-point FFT (issue #30).

  regen -> Icarus vs the bit-accurate model on the sim/vectors.py sets ->
  Yosys map to sky130_fd_sc_hd at tt_025C_1v80 -> append a record to
  ../measurements/fft256-smoke.json

Exits non-zero on any RTL/model mismatch (count and first differing index are
printed), on a regenerated tree that differs from the committed one, or on a
macro/SRAM cell in the mapped netlist. Run through `make smoke-fft256`.
Environment: PERTURB=<i> flips one DUT output bit (negative control, no record).
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "sim"))
sys.path.insert(0, str(HERE))

import flow_tools  # noqa: E402
import fixedpoint_model  # noqa: E402
import reference  # noqa: E402
import vectors  # noqa: E402

PARAMS = ROOT / "rtl/params/fft256.params"
RECORD = ROOT / "measurements/fft256-smoke.json"
BUILD = HERE / "sim_build" / "smoke_fft256"
TOOLS = ("icarus_verilog", "verilator", "yosys", "cocotb", "python")
MISMATCH_TEXT = "RTL output differs from bit-accurate model"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout.strip()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regen_unchanged():
    """Regenerate rtl/generated and require it to equal the committed tree."""
    run(["bash", str(ROOT / "rtl/regen.sh")])
    diff = run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "rtl/generated"])
    if diff:
        sys.exit(f"regenerated rtl/generated differs from the committed tree:\n{diff}")


def installed_tools():
    got = flow_tools.installed()
    return {k: got[k] for k in TOOLS}, {k: [got[k], flow_tools.PINS[k]] for k in TOOLS if got[k] != flow_tools.PINS[k]}


def frame_sets(p):
    return {n: vectors.generate_frames(n, n=p.size, width=p.input_width) for n in vectors.VECTOR_SETS}


def pack(frames, width):
    mask = (1 << width) - 1
    words = []
    for f in frames:
        for z in f:
            words.append(f"{int(z.real) & mask:04x}{int(z.imag) & mask:04x}")
    return words


def signed16(x):
    return x - 0x10000 if x & 0x8000 else x


def icarus(words, perturb):
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "stim.hex").write_text("\n".join(words) + "\n")
    gen = sorted((ROOT / "rtl/generated").glob("*.v"))
    run(["iverilog", "-g2012", f"-Ptb_fft256_smoke.NSAMP={len(words)}", "-o", str(BUILD / "sim.vvp"),
         str(HERE / "tb_fft256_smoke.v"), *map(str, gen)])
    args = ["vvp", "sim.vvp"] + ([f"+perturb={perturb}"] if perturb is not None else [])
    log = run(args, cwd=BUILD)
    cap = re.search(r"captured=(\d+) first_valid_cycle=(-?\d+)", log)
    if not cap or int(cap.group(1)) != len(words):
        sys.exit(f"Icarus run captured too few output samples: {log}")
    lines = (BUILD / "out.hex").read_text().split()
    re_ = np.array([signed16(int(w[:4], 16)) for w in lines], dtype=np.int64)
    im_ = np.array([signed16(int(w[4:], 16)) for w in lines], dtype=np.int64)
    return re_, im_, int(cap.group(2))


def compare(model, sets, p, perturb):
    names = list(sets)
    frames = np.concatenate([sets[n] for n in names])
    words = pack(frames, p.input_width)
    dut_re, dut_im, first_valid = icarus(words, perturb)
    res = model.run(frames.real.astype(np.int64), frames.imag.astype(np.int64))
    exp_re, exp_im = res.re.reshape(-1), res.im.reshape(-1)
    bad = np.nonzero((dut_re != exp_re) | (dut_im != exp_im))[0]
    out = {"samples": len(words), "mismatches": int(len(bad)), "first_valid_cycle": first_valid}
    if len(bad):
        i = int(bad[0])
        print(f"{MISMATCH_TEXT}: {len(bad)} of {len(words)} samples differ; first at index {i} "
              f"(frame {i // p.size}, bin {i % p.size}): dut=({dut_re[i]},{dut_im[i]}) "
              f"model=({exp_re[i]},{exp_im[i]})", file=sys.stderr)
    return out


def simulated_sqnr(model, sets):
    out = {}
    for name, frames in sets.items():
        model.stats = fixedpoint_model.Stats(len(model.p.stage_widths))
        out[name] = {"min_sqnr_db": round(reference.set_sqnr_db(frames, model.candidate), 2),
                     "overflow_components": sum(model.stats.overflow)}
    return out


def check_no_macros(cells):
    bad = sorted(c for c in cells if not c.startswith("sky130_fd_sc_hd__") or "sram" in c.lower())
    if bad:
        sys.exit(f"mapped netlist contains non-standard-cell or SRAM cells: {bad}")


def append_record(record):
    data = json.loads(RECORD.read_text()) if RECORD.exists() else {"records": []}
    data["records"].append(record)  # append-only: earlier records are never rewritten
    RECORD.write_text(json.dumps(data, indent=2) + "\n")


def main():
    perturb = int(os.environ["PERTURB"]) if "PERTURB" in os.environ else None
    regen_unchanged()
    model = fixedpoint_model.FixedPointFFT.from_file(PARAMS)
    p = model.p
    sets = frame_sets(p)
    cmp_ = compare(model, sets, p, perturb)
    if cmp_["mismatches"]:
        sys.exit(1)
    print(f"Icarus matches the model bit-exactly: {cmp_['samples']} samples over {list(sets)}")
    if perturb is not None:
        sys.exit("perturbed run unexpectedly matched the model")
    sqnr = simulated_sqnr(model, sets)
    design = flow_tools.run_yosys("synth_fft256.ys")
    check_no_macros(design["num_cells_by_type"])
    tools, drift = installed_tools()
    pdk = flow_tools.PINS["pdk"]
    stim = hashlib.sha256("\n".join(pack(np.concatenate(list(sets.values())), p.input_width)).encode()).hexdigest()
    record = {
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "module": "fft256",
        "note": "smoke run of the generated top at PLACEHOLDER widths; single corner, cell count and area only; no timing claim",
        "generator": {
            "repo_head": run(["git", "-C", str(ROOT), "rev-parse", "HEAD"]),
            "generator_last_commit": run(["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", "rtl/gen"]),
            "parameter_file": str(PARAMS.relative_to(ROOT)),
            "parameter_file_sha256": sha256(PARAMS),
            "generated_tree_matches_regen": True,
        },
        "model": {
            "id": fixedpoint_model.MODEL_ID,
            "input_width": p.input_width, "stage_widths": list(p.stage_widths),
            "output_width": p.output_width, "twiddle_width": p.twiddle_width,
            "rounding": p.rounding, "output_order": p.output_order,
        },
        "vectors": {
            "sets": {n: {"frames": int(len(f)), "samples_per_frame": p.size} for n, f in sets.items()},
            "stimulus_sha256": stim,
        },
        "rtl_vs_model": {**cmp_, "bit_exact": True},
        "sqnr_simulated": {"label": "simulated: model vs double precision, not measured", "sets": sqnr},
        "liberty_corner": pdk["liberty_corner"],
        "liberty_file": pdk["liberty_file"],
        "pdk_revision": pdk["revision"],
        "tool_versions": tools,
        "tool_version_drift_vs_pins": drift,
        "cell_count": design["num_cells"],
        "cells_by_type": design["num_cells_by_type"],
        "area_um2": design.get("area"),
    }
    append_record(record)
    print(f"appended record to {RECORD.relative_to(ROOT)}: {record['cell_count']} cells, "
          f"area {record['area_um2']} um2 at {record['liberty_corner']}")


if __name__ == "__main__":
    main()
