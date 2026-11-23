"""Toolchain pin check for the verification flows.

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
VERILATOR = os.environ.get("VERILATOR", "verilator")


def _out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def installed():
    import cocotb

    return {
        "icarus_verilog": re.search(r"version (\d+\.\d+)", _out(["iverilog", "-V"])).group(1),
        "verilator": re.search(r"Verilator (\d+\.\d+)", _out([VERILATOR, "--version"])).group(1),
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


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
