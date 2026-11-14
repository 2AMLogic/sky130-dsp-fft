# Verification flow for the generated FFT (see README.md). Run from verification/.
# Targets: check-tools lint lint-negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl lint-wrapper fft-bench fft-bench-negctl all clean
PYTHON    ?= ../.venv/bin/python
ROOT      ?= $(abspath ..)
# Repo root on PYTHONPATH: the sim and verification entry points import the
# model as a package (`from sim import ...`) instead of editing sys.path
# themselves, and the cocotb runner hands this process's sys.path to the
# simulator it spawns. A PYTHONPATH set by the caller is kept.
PYPATH     = PYTHONPATH=$(ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))
VERILATOR ?= verilator
YOSYS     ?= yosys
PDK_ROOT  ?= $(HOME)/.ciel
# Verilator warning the seeded-defect lint run must fail on (see lint-negctl).
LINT_NEGCTL_EXPECT ?= %Warning-WIDTHTRUNC
# Assertion text the wrong-reference run must fail on (see ../sim/test_reference.py).
SQNR_NEGCTL_EXPECT ?= Reference FFT differs from numpy.fft.fft
# Assertion text the floor-ties mutant run must fail on (see ../sim/test_fixedpoint_model.py).
FXP_NEGCTL_EXPECT ?= convergent tie rounding wrong
# Assertion text the perturbed-DUT smoke run must fail on (see test_fft256_smoke.py).
SMOKE_NEGCTL_EXPECT ?= RTL output differs from bit-accurate model
# Assertion text the perturbed-output cocotb stream bench must fail on (see test_fft256_stream.py).
FFT_BENCH_NEGCTL_EXPECT ?= stream output differs from bit-accurate model
# The four *_negctl targets below run their mutant through negctl.sh, which
# owns the must-fail-for-the-intended-reason contract (lint-negctl seeds its
# defect into a copied tree first and keeps its own recipe).

.PHONY: all check-tools lint lint-negctl lint-wrapper sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl fft-bench fft-bench-negctl clean

all: check-tools lint lint-negctl lint-wrapper sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl fft-bench fft-bench-negctl

check-tools:
	$(PYTHON) flow_tools.py check

# Lint the generated core at its real top. -Wall stays on; the only waivers are
# the reasoned, rtl/generated-scoped ones in lint_waivers.vlt.
lint:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256 lint_waivers.vlt ../rtl/generated/*.v

# Lint a copy of the generated tree with a seeded defect (an 8-bit constant into
# a 4-bit wire, a class that is not waived). The clean copy must pass first; the
# seeded copy must fail AND carry LINT_NEGCTL_EXPECT, so a missing file or crash
# does not count as "caught". rtl/generated itself is never modified.
lint-negctl:
	@rm -rf sim_build/lint_negctl
	@mkdir -p sim_build/lint_negctl/rtl/generated
	@cp ../rtl/generated/*.v sim_build/lint_negctl/rtl/generated/
	@if ! $(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256 lint_waivers.vlt sim_build/lint_negctl/rtl/generated/*.v > sim_build/lint_negctl/clean.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: clean copy of the generated tree does not lint (see sim_build/lint_negctl/clean.out)"; exit 1; fi
	@sed -i '0,/^endmodule/s//wire [3:0] seeded_trunc = 8'"'"'hFF;\nendmodule/' sim_build/lint_negctl/rtl/generated/fft_rnd.v
	@if grep -q seeded_trunc ../rtl/generated/fft_rnd.v || ! grep -q seeded_trunc sim_build/lint_negctl/rtl/generated/fft_rnd.v; then \
	  echo "NEGATIVE CONTROL FAILED: defect not seeded into the copy only"; exit 1; fi
	@if $(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256 lint_waivers.vlt sim_build/lint_negctl/rtl/generated/*.v > sim_build/lint_negctl/seeded.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: seeded defect passed lint"; exit 1; \
	elif ! grep -qF "$(LINT_NEGCTL_EXPECT)" sim_build/lint_negctl/seeded.out; then \
	  echo "NEGATIVE CONTROL FAILED: seeded defect failed without the expected text '$(LINT_NEGCTL_EXPECT)' (see sim_build/lint_negctl/seeded.out)"; exit 1; \
	else echo "negative control OK: seeded defect caught by lint"; fi

# Vector sets and double-precision SQNR reference (pure Python + numpy).
sqnr-ref:
	$(PYPATH) $(PYTHON) -m sim.test_reference

# Same tests with a wrong reference (I/Q swapped); must fail on the intended text.
sqnr-ref-negctl:
	@mkdir -p sim_build
	@./negctl.sh "wrong reference" "the tests" "$(SQNR_NEGCTL_EXPECT)" sim_build/sqnr_negctl.out -- \
	  env REF_MUTANT=swap_iq $(PYPATH) $(PYTHON) -m sim.test_reference

# Bit-accurate fixed-point model tests, the no-overflow amplitude sweep tests
# and the candidate growth-schedule sweep tests (pure Python + numpy).
fxp-model:
	$(PYPATH) $(PYTHON) -m sim.test_fixedpoint_model
	$(PYPATH) $(PYTHON) -m sim.test_overflow_range
	$(PYPATH) $(PYTHON) -m sim.test_schedule_sweep

# Same tests with a flooring rounder; must fail on the convergent-tie check.
fxp-model-negctl:
	@mkdir -p sim_build
	@./negctl.sh "flooring rounder" "the tests" "$(FXP_NEGCTL_EXPECT)" sim_build/fxp_negctl.out -- \
	  env FXP_MUTANT=floor_ties $(PYPATH) $(PYTHON) -m sim.test_fixedpoint_model

# End-to-end smoke of the generated 256-point FFT: regen, Icarus vs the model,
# Yosys at tt_025C_1v80; appends a record to ../measurements/fft256-smoke.json.
# Tool-version drift is recorded, not fatal (run `make check-tools` for the pins).
smoke-fft256:
	PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYPATH) $(PYTHON) test_fft256_smoke.py

# One DUT output bit flipped; must fail on the mismatch text and write no record.
smoke-fft256-negctl:
	@mkdir -p sim_build
	@./negctl.sh "perturbed DUT" "the smoke" "$(SMOKE_NEGCTL_EXPECT)" sim_build/smoke_negctl.out -- \
	  env PERTURB=1000 PDK_ROOT=$(PDK_ROOT) YOSYS=$(YOSYS) $(PYPATH) $(PYTHON) test_fft256_smoke.py

# Hand-written streaming wrapper (rtl/wrapper): lint it against a port-only stub
# of the generated core (the bit-exact bench is fft-bench).
lint-wrapper:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256_stream ../rtl/wrapper/fft256_stream.sv stubs/fft256_stub.sv

# cocotb bench of the streaming wrapper over the generated core: bit-exact vs
# the model on the sim/vectors.py sets, handshake/back-pressure/reset tests.
fft-bench:
	$(PYPATH) $(PYTHON) test_fft256_stream.py

# One captured output bit flipped (FFT_BENCH_PERTURB); must fail on the
# mismatch text, not on a compile error or runner crash. Writes no record.
fft-bench-negctl:
	@mkdir -p sim_build
	@./negctl.sh "perturbed output" "the bench" "$(FFT_BENCH_NEGCTL_EXPECT)" sim_build/fft_bench_negctl.out -- \
	  env FFT_BENCH_PERTURB=1000 $(PYPATH) $(PYTHON) test_fft256_stream.py

clean:
	rm -rf sim_build results.xml
