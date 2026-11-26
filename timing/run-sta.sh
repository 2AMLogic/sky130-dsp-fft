#!/bin/sh
# Pre-route STA evidence for the committed gate-level netlist (issue #158).
#
# Tool versions used for the committed reports (recorded beside the command):
#   klayout-tools 0.9.2 (published release, run via uvx; verilog-mode
#     `klt sta` with `pdk.corners` needs it -- newer than the 0.8.0 that
#     signoff.yml pins for `klt signoff`, used for these reports only; the
#     item 1/9/10 attestation recipes and their pins are unchanged)
#   openroad 26Q3-1510-g6cb3f2b704 (resolved from $PATH by klt sta)
#   PDK: sky130A, open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7 (the
#     revision verification/toolchain.json pins), resolved via find_pdk()
#     standard roots (provenance.pdk in each report records what ran)
#
# Run from anywhere; the script cds to the repository root because klt sta
# resolves its scratch dir under the cwd (klayout-tools#5753). Reproduces
# both committed reports in one documented command:
#
#   ./timing/run-sta.sh
#
# Freshness of these reports is by re-run until klt sta grows --check/--rerun
# (klayout-tools#5841).
set -eu
cd "$(dirname "$0")/.."

tmpdir=$(mktemp -d timing/.run-sta.XXXXXX)
cleanup() {
    rm -rf "$tmpdir"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

signoff_tmp="$tmpdir/fft256.sta.report.json"
all_corners_tmp="$tmpdir/fft256.sta.all-corners.report.json"

uvx --from "klayout-tools==0.9.2" klt sta timing/fft256.sta.request.json \
    --format json > "$signoff_tmp"

uvx --from "klayout-tools==0.9.2" klt sta timing/fft256.sta.all-corners.request.json \
    --format json > "$all_corners_tmp"

mv -f "$signoff_tmp" timing/fft256.sta.report.json
mv -f "$all_corners_tmp" timing/fft256.sta.all-corners.report.json
