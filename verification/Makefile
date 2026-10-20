# Flow for the placeholder module (see README.md). Run from verification/.
# Targets: check-tools lint sim negctl synth all clean
PYTHON    ?= ../.venv/bin/python
VERILATOR ?= verilator
YOSYS     ?= yosys
PDK_ROOT  ?= $(HOME)/.ciel

.PHONY: all check-tools lint sim negctl synth clean

all: check-tools lint sim negctl

check-tools:
	$(PYTHON) flow_tools.py check

lint:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module placeholder_add ../rtl/placeholder/*.sv

sim:
	DUT=placeholder $(PYTHON) test_placeholder.py

# The mutant must make the same test fail; this target succeeds only if it does.
negctl:
	@mkdir -p sim_build
	@if DUT=mutant $(PYTHON) test_placeholder.py > sim_build/negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: mutant passed the test"; exit 1; \
	else echo "negative control OK: mutant caught by the test"; fi

synth:
	PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYTHON) flow_tools.py synth

clean:
	rm -rf sim_build results.xml
