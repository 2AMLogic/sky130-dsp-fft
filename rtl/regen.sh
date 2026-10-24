#!/bin/sh
# Regenerate RTL from the pinned generator and a committed parameter file.
# Stub: no RTL yet.
GENERATOR_REPO=https://github.com/ZipCPU/dblclockfft
GENERATOR_COMMIT=3378b77d83a98b06184656a5cb9b54e50dfe4485
PARAMS="${1:-$(dirname "$0")/params/fft256.params}"
echo "generator: $GENERATOR_REPO @ $GENERATOR_COMMIT"
echo "params:    $PARAMS"
echo "regen.sh: no RTL yet" >&2
exit 1
