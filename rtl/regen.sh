#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Regenerate the committed RTL from a parameter file. Never hand-edit rtl/generated/.
# usage: rtl/regen.sh [PARAMS_FILE]   (default rtl/params/fft256.params)
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
params="${1:-$root/rtl/params/fft256.params}"
out="$root/rtl/generated"
rm -rf "$out"
cd "$root"
python3 -m rtl.gen "$params" "$out" >/dev/null
echo "regenerated $(ls "$out" | wc -l) files in rtl/generated from $(basename "$params")"
