#!/bin/sh
# Shared runner for the negative-control make targets (see Makefile): run a
# mutant command that must fail, and count it as caught only when its log
# carries the expected assertion text -- so a crash or a missing file does not
# count as "caught".
#
# Usage:
#   negctl.sh <label> <noun> <expected-text> <log-path> -- <command...>
#
# Outcomes:
#   command succeeds        -> "NEGATIVE CONTROL FAILED: <label> passed <noun>"; exit 1
#   log lacks expected text -> "NEGATIVE CONTROL FAILED: <label> failed without
#                              the expected text '<text>' (see <log>)"; exit 1
#   otherwise               -> "negative control OK: <label> caught by <noun>"
set -u

label=$1; shift
noun=$1; shift
expect=$1; shift
log=$1; shift
if [ "${1:-}" = "--" ]; then shift; fi

if "$@" > "$log" 2>&1; then
  echo "NEGATIVE CONTROL FAILED: $label passed $noun"
  exit 1
elif ! grep -qF "$expect" "$log"; then
  echo "NEGATIVE CONTROL FAILED: $label failed without the expected text '$expect' (see $log)"
  exit 1
else
  echo "negative control OK: $label caught by $noun"
fi
