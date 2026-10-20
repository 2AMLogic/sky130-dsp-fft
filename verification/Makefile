# Flow for the placeholder module (see README.md). Run from verification/.
# Targets: check-tools lint sim negctl synth all clean
PYTHON    ?= ../.venv/bin/python
VERILATOR ?= verilator
YOSYS     ?= yosys
PDK_ROOT  ?= $(HOME)/.ciel
# Assertion text the mutant run must fail on (see test_placeholder.py).
NEGCTL_EXPECT ?= DUT output differs from Python model

.PHONY: all check-tools lint sim negctl synth clean

all: check-tools lint sim negctl

check-tools:
	$(PYTHON) flow_tools.py check

lint:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module placeholder_add ../rtl/placeholder/*.sv

sim:
	DUT=placeholder $(PYTHON) test_placeholder.py

# The mutant must make the same test fail on the intended mismatch; this target
# succeeds only if it exits non-zero and its output carries NEGCTL_EXPECT, so a
# compile error or runner crash does not count as "caught".
negctl:
	@mkdir -p sim_build
	@if DUT=mutant $(PYTHON) test_placeholder.py > sim_build/negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: mutant passed the test"; exit 1; \
	elif ! grep -qF "$(NEGCTL_EXPECT)" sim_build/negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: mutant failed without the expected text '$(NEGCTL_EXPECT)' (see sim_build/negctl.out)"; exit 1; \
	else echo "negative control OK: mutant caught by the test"; fi

synth:
	PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYTHON) flow_tools.py synth

clean:
	rm -rf sim_build results.xml
