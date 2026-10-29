#!/bin/sh
# Regenerate RTL from the pinned generator and a committed parameter file.
# Stub: no RTL yet. The generator is the project's own Apache-2.0 FFT
# generator (spec/decisions/0001-generator.md), added by issue #27, which
# also adds its pinned commit here.
PARAMS="${1:-$(dirname "$0")/params/fft256.params}"
echo "generator: project FFT generator (issue #27), not yet added"
echo "params:    $PARAMS"
echo "regen.sh: no RTL yet" >&2
exit 1
