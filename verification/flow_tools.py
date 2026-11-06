"""Toolchain pin check and the shared Yosys runner.

  flow_tools.py check   fail unless installed tool versions match toolchain.json
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


def run_yosys(script_name):
    """Run a Yosys script at the pinned liberty corner; return Yosys's `design` stat dict.

    `${LIBERTY}` and `${STAT_JSON}` in the script are substituted. Does not check
    tool versions: callers decide whether drift is fatal or recorded.
    """
    pdk = PINS["pdk"]
    root = Path(os.environ.get("PDK_ROOT", Path.home() / ".ciel"))
    liberty = root / "ciel" / pdk["name"] / "versions" / pdk["revision"] / pdk["liberty_relpath"]
    if not liberty.is_file():
        sys.exit(f"liberty not found: {liberty} (pdk revision {pdk['revision']})")
    build = HERE / "sim_build"
    build.mkdir(exist_ok=True)
    stem = Path(script_name).stem
    stat = build / f"{stem}_stat.json"
    script = (HERE / script_name).read_text()
    script = script.replace("${LIBERTY}", str(liberty)).replace("${STAT_JSON}", str(stat))
    resolved = build / f"{stem}.resolved.ys"
    resolved.write_text(script)
    run = subprocess.run([YOSYS, "-q", "-l", str(build / f"{stem}.log"), "-s", str(resolved)], cwd=HERE)
    if run.returncode:
        sys.exit(f"yosys failed; see verification/sim_build/{stem}.log")
    return json.loads(stat.read_text())["design"]


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
