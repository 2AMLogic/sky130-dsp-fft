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
YOSYS = os.environ.get("YOSYS", "yosys")
VERILATOR = os.environ.get("VERILATOR", "verilator")


def _out(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _cocotb_version():
    import cocotb

    return cocotb.__version__


# One probe per tool pin (every toolchain.json key but "pdk"). installed()
# invokes only the requested binaries, so the smoke-fft256 flow can probe its
# four tools without Yosys or a PDK while check() enforces every pin.
_PROBES = {
    "icarus_verilog": lambda: re.search(r"version (\d+\.\d+)", _out(["iverilog", "-V"])).group(1),
    "verilator": lambda: re.search(r"Verilator (\d+\.\d+)", _out([VERILATOR, "--version"])).group(1),
    "yosys": lambda: re.search(r"Yosys (\d+\.\d+)", _out([YOSYS, "-V"])).group(1),
    "cocotb": _cocotb_version,
    "python": lambda: "%d.%d" % sys.version_info[:2],
}


def installed(tools=None):
    if tools is None:
        tools = [k for k in PINS if k != "pdk"]
    return {k: _PROBES[k]() for k in tools}


def check():
    pins = {k: v for k, v in PINS.items() if k != "pdk"}
    unprobed = sorted(k for k in pins if k not in _PROBES)
    if unprobed:
        print(f"toolchain mismatch: no version probe for pinned tool(s): {', '.join(unprobed)}", file=sys.stderr)
        sys.exit(1)
    got = installed()
    bad = {k: (got[k], pins[k]) for k in got if got[k] != pins[k]}
    for k, (have, want) in bad.items():
        print(f"toolchain mismatch: {k} installed {have}, pinned {want}", file=sys.stderr)
    if bad:
        sys.exit(1)
    print("toolchain matches verification/toolchain.json")


if __name__ == "__main__":
    {"check": check}[sys.argv[1]]()
