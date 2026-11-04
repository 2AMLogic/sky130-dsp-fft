# Flow for the placeholder module (see README.md). Run from verification/.
# Targets: check-tools lint sim negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl synth smoke-fft256 smoke-fft256-negctl lint-wrapper sim-wrapper sim-wrapper-negctl fft-bench fft-bench-negctl all clean
PYTHON    ?= ../.venv/bin/python
VERILATOR ?= verilator
YOSYS     ?= yosys
PDK_ROOT  ?= $(HOME)/.ciel
# Assertion text the mutant run must fail on (see test_placeholder.py).
NEGCTL_EXPECT ?= DUT output differs from Python model
# Assertion text the wrong-reference run must fail on (see ../sim/test_reference.py).
SQNR_NEGCTL_EXPECT ?= Reference FFT differs from numpy.fft.fft
# Assertion text the floor-ties mutant run must fail on (see ../sim/test_fixedpoint_model.py).
FXP_NEGCTL_EXPECT ?= convergent tie rounding wrong
# Assertion text the perturbed-DUT smoke run must fail on (see test_fft256_smoke.py).
SMOKE_NEGCTL_EXPECT ?= RTL output differs from bit-accurate model
# Assertion text the perturbed-output cocotb stream bench must fail on (see test_fft256_stream.py).
FFT_BENCH_NEGCTL_EXPECT ?= stream output differs from bit-accurate model

.PHONY: all check-tools lint lint-wrapper sim-wrapper sim-wrapper-negctl sim negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl synth smoke-fft256 smoke-fft256-negctl fft-bench fft-bench-negctl clean

all: check-tools lint sim negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl fft-bench fft-bench-negctl

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

# Vector sets and double-precision SQNR reference (pure Python + numpy).
sqnr-ref:
	$(PYTHON) ../sim/test_reference.py

# Same tests with a wrong reference (I/Q swapped); must fail on the intended text.
sqnr-ref-negctl:
	@mkdir -p sim_build
	@if REF_MUTANT=swap_iq $(PYTHON) ../sim/test_reference.py > sim_build/sqnr_negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: wrong reference passed the tests"; exit 1; \
	elif ! grep -qF "$(SQNR_NEGCTL_EXPECT)" sim_build/sqnr_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: wrong reference failed without the expected text '$(SQNR_NEGCTL_EXPECT)' (see sim_build/sqnr_negctl.out)"; exit 1; \
	else echo "negative control OK: wrong reference caught by the tests"; fi

# Bit-accurate fixed-point model tests (pure Python + numpy).
fxp-model:
	$(PYTHON) ../sim/test_fixedpoint_model.py

# Same tests with a flooring rounder; must fail on the convergent-tie check.
fxp-model-negctl:
	@mkdir -p sim_build
	@if FXP_MUTANT=floor_ties $(PYTHON) ../sim/test_fixedpoint_model.py > sim_build/fxp_negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: flooring rounder passed the tests"; exit 1; \
	elif ! grep -qF "$(FXP_NEGCTL_EXPECT)" sim_build/fxp_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: flooring rounder failed without the expected text '$(FXP_NEGCTL_EXPECT)' (see sim_build/fxp_negctl.out)"; exit 1; \
	else echo "negative control OK: flooring rounder caught by the tests"; fi

synth:
	PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYTHON) flow_tools.py synth

# End-to-end smoke of the generated 256-point FFT: regen, Icarus vs the model,
# Yosys at tt_025C_1v80; appends a record to ../measurements/fft256-smoke.json.
# Tool-version drift is recorded, not fatal (run `make check-tools` for the pins).
smoke-fft256:
	PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYTHON) test_fft256_smoke.py

# One DUT output bit flipped; must fail on the mismatch text and write no record.
smoke-fft256-negctl:
	@mkdir -p sim_build
	@if PERTURB=1000 PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYTHON) test_fft256_smoke.py > sim_build/smoke_negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed DUT passed the smoke"; exit 1; \
	elif ! grep -qF "$(SMOKE_NEGCTL_EXPECT)" sim_build/smoke_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed DUT failed without the expected text '$(SMOKE_NEGCTL_EXPECT)' (see sim_build/smoke_negctl.out)"; exit 1; \
	else echo "negative control OK: perturbed DUT caught by the smoke"; fi

# Hand-written streaming wrapper (rtl/wrapper): lint it against a port-only stub
# of the generated core, then smoke it in Icarus against the real core.
lint-wrapper:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256_stream ../rtl/wrapper/fft256_stream.sv stubs/fft256_stub.sv

sim-wrapper:
	@mkdir -p sim_build
	iverilog -g2012 -o sim_build/stream.vvp tb_fft256_stream.sv ../rtl/wrapper/fft256_stream.sv ../rtl/generated/*.v
	vvp sim_build/stream.vvp | tee sim_build/stream.out
	@grep -q "^PASS fft256_stream smoke" sim_build/stream.out

# One output bit flipped at step 600; must fail on the data mismatch.
sim-wrapper-negctl:
	@mkdir -p sim_build
	iverilog -g2012 -DNEGCTL -o sim_build/stream_negctl.vvp tb_fft256_stream.sv ../rtl/wrapper/fft256_stream.sv ../rtl/generated/*.v
	@if vvp sim_build/stream_negctl.vvp > sim_build/stream_negctl.out 2>&1 && grep -q "^PASS" sim_build/stream_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed wrapper output passed"; exit 1; \
	elif ! grep -qF "MISMATCH data" sim_build/stream_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: no data mismatch reported (see sim_build/stream_negctl.out)"; exit 1; \
	else echo "negative control OK: perturbed wrapper output caught"; fi

# cocotb bench of the streaming wrapper over the generated core: bit-exact vs
# the model on the sim/vectors.py sets, handshake/back-pressure/reset tests.
fft-bench:
	$(PYTHON) test_fft256_stream.py

# One captured output bit flipped (FFT_BENCH_PERTURB); must fail on the
# mismatch text, not on a compile error or runner crash. Writes no record.
fft-bench-negctl:
	@mkdir -p sim_build
	@if FFT_BENCH_PERTURB=1000 $(PYTHON) test_fft256_stream.py > sim_build/fft_bench_negctl.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed output passed the bench"; exit 1; \
	elif ! grep -qF "$(FFT_BENCH_NEGCTL_EXPECT)" sim_build/fft_bench_negctl.out; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed output failed without the expected text '$(FFT_BENCH_NEGCTL_EXPECT)' (see sim_build/fft_bench_negctl.out)"; exit 1; \
	else echo "negative control OK: perturbed stream output caught by the bench"; fi

clean:
	rm -rf sim_build results.xml
