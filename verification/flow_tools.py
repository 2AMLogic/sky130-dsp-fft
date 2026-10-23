"""Toolchain pin check and Yosys smoke-synthesis record writer.

  flow_tools.py check   fail unless installed tool versions match toolchain.json
  flow_tools.py synth   run synth.ys at the pinned liberty corner and write
                        ../measurements/synth-placeholder.json
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = json.loads((HERE / "toolchain.json").read_text())
YOSYS = os.environ.get("YOSYS", "yosys")
VERILATOR = os.environ.get("VERILATOR", "verilator")


def _out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def installed():
    import cocotb

    return {
        "icarus_verilog": re.search(r"version (\d+\.\d+)", _out(["iverilog", "-V"])).group(1),
        "verilator": re.search(r"Verilator (\d+\.\d+)", _out([VERILATOR, "--version"])).group(1),
        "yosys": re.search(r"Yosys (\d+\.\d+)", _out([YOSYS, "-V"])).group(1),
        "cocotb": cocotb.__version__,
        "python": "%d.%d" % sys.version_info[:2],
    }


def check():
    got = installed()
    bad = {k: (got[k], PINS[k]) for k in got if got[k] != PINS[k]}
    for k, (have, want) in bad.items():
        print(f"toolchain mismatch: {k} installed {have}, pinned {want}", file=sys.stderr)
    if bad:
        sys.exit(1)
    print("toolchain matches verification/toolchain.json")


def synth():
    check()
    pdk = PINS["pdk"]
    root = Path(os.environ.get("PDK_ROOT", Path.home() / ".ciel"))
    liberty = root / "ciel" / pdk["name"] / "versions" / pdk["revision"] / pdk["liberty_relpath"]
    if not liberty.is_file():
        sys.exit(f"liberty not found: {liberty} (pdk revision {pdk['revision']})")
    build = HERE / "sim_build"
    build.mkdir(exist_ok=True)
    stat = build / "synth_stat.json"
    script = (HERE / "synth.ys").read_text()
    script = script.replace("${LIBERTY}", str(liberty)).replace("${STAT_JSON}", str(stat))
    resolved = build / "synth.resolved.ys"
    resolved.write_text(script)
    run = subprocess.run([YOSYS, "-q", "-l", str(build / "synth.log"), "-s", str(resolved)], cwd=HERE)
    if run.returncode:
        sys.exit("yosys failed; see verification/sim_build/synth.log")
    design = json.loads(stat.read_text())["design"]
    record = {
        "module": "placeholder_add",
        "note": "flow smoke on a placeholder module; not a design result",
        "liberty_corner": pdk["liberty_corner"],
        "liberty_file": pdk["liberty_file"],
        "pdk_revision": pdk["revision"],
        "tool_versions": {k: PINS[k] for k in ("icarus_verilog", "verilator", "yosys", "cocotb")},
        "cell_count": design["num_cells"],
        "cells_by_type": design["num_cells_by_type"],
        "area_um2": design.get("area"),
    }
    out = HERE.parent / "measurements" / "synth-placeholder.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {out.relative_to(HERE.parent)}: {record['cell_count']} cells")


if __name__ == "__main__":
    {"check": check, "synth": synth}[sys.argv[1]]()
