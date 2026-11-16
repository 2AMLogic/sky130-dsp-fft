# Verification flow for the generated FFT (see README.md). Run from verification/.
# Targets: check-tools lint lint-negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl lint-wrapper fft-bench fft-bench-negctl gen-exact gen-exact-negctl gen-unit gen-unit-negctl all clean
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
# Assertion text the perturbed multi-configuration exact run must fail on (see test_gen_exact.py).
GEN_EXACT_NEGCTL_EXPECT ?= generated RTL output differs from bit-accurate model
# Assertion message the perturbed-regen-copy run must fail on: the byte-compare
# assertion in Determinism.test_committed_rtl_matches_fresh_regen appends the
# mismatching file's name ("fft256.v") to its message, so the trailing
# ": fft256.v" proves the comparison fired rather than an import error or crash.
GEN_UNIT_NEGCTL_EXPECT ?= : fft256.v
# The six *_negctl targets below run their mutant through negctl.sh, which
# owns the must-fail-for-the-intended-reason contract (lint-negctl seeds its
# defect into a copied tree first and keeps its own recipe).

.PHONY: all check-tools lint lint-negctl lint-wrapper sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl fft-bench fft-bench-negctl gen-exact gen-exact-negctl gen-unit gen-unit-negctl clean

all: check-tools lint lint-negctl lint-wrapper sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl fft-bench fft-bench-negctl gen-exact gen-exact-negctl gen-unit gen-unit-negctl

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
	$(PYPATH) $(PYTHON) -m unittest sim.test_reference

# Same tests with a wrong reference (I/Q swapped); must fail on the intended text.
sqnr-ref-negctl:
	@mkdir -p sim_build
	@./negctl.sh "wrong reference" "the tests" "$(SQNR_NEGCTL_EXPECT)" sim_build/sqnr_negctl.out -- \
	  env REF_MUTANT=swap_iq $(PYPATH) $(PYTHON) -m unittest sim.test_reference

# Bit-accurate fixed-point model tests, the no-overflow amplitude sweep tests,
# the candidate growth-schedule sweep tests and the per-size model record tests
# (pure Python + numpy).
fxp-model:
	$(PYPATH) $(PYTHON) -m unittest sim.test_fixedpoint_model
	$(PYPATH) $(PYTHON) -m unittest sim.test_overflow_range
	$(PYPATH) $(PYTHON) -m unittest sim.test_schedule_sweep
	# test_records.py keeps its own runner: its tests are module-level
	# functions, which `-m unittest` would not collect (a vacuous pass).
	$(PYPATH) $(PYTHON) -m sim.test_records
	$(PYPATH) $(PYTHON) -m sim.test_model_sizes

# Same tests with a flooring rounder; must fail on the convergent-tie check.
fxp-model-negctl:
	@mkdir -p sim_build
	@./negctl.sh "flooring rounder" "the tests" "$(FXP_NEGCTL_EXPECT)" sim_build/fxp_negctl.out -- \
	  env FXP_MUTANT=floor_ties $(PYPATH) $(PYTHON) -m unittest sim.test_fixedpoint_model

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

# Bit-exact check of the generated FFT against the model at six configurations
# (sizes 4/16/64/256, natural/bitrev, pipeline 0/1): fresh regen in a temp dir,
# Icarus, every captured output component equal to FixedPointFFT.run (issue #90).
gen-exact:
	$(PYPATH) $(PYTHON) test_gen_exact.py

# One captured output component flipped per configuration (GEN_EXACT_PERTURB);
# must fail on the mismatch text, not on a compile error or runner crash.
gen-exact-negctl:
	@mkdir -p sim_build
	@./negctl.sh "perturbed DUT" "the exact check" "$(GEN_EXACT_NEGCTL_EXPECT)" sim_build/gen_exact_negctl.out -- \
	  env GEN_EXACT_PERTURB=1000 $(PYPATH) $(PYTHON) test_gen_exact.py

# Generator unit tests (rtl/gen/tests/test_gen.py): regen byte-determinism,
# committed rtl/generated == fresh regen from rtl/params/fft256.params, SPDX
# headers, parameter variations and invalid-parameter rejection. Pure Python;
# the Icarus/Yosys acceptance class skips, with a reason, when a tool is absent.
gen-unit:
	$(PYPATH) $(PYTHON) -m unittest rtl.gen.tests.test_gen

# One byte appended to a copy of the whole rtl/ tree, on PYTHONPATH ahead of
# the committed tree (make runs from verification/, which has no rtl/ package,
# so the copy shadows it). The copy's committed-vs-regen check must fail on
# the byte-compare assertion (: fft256.v), not on an import error or crash.
# rtl/generated itself is never modified.
gen-unit-negctl:
	@rm -rf sim_build/gen_unit_negctl
	@mkdir -p sim_build/gen_unit_negctl
	@cp -r ../rtl sim_build/gen_unit_negctl/rtl
	@printf 'x' >> sim_build/gen_unit_negctl/rtl/generated/fft256.v
	@if [ "$$(( $$(wc -c < ../rtl/generated/fft256.v) + 1 ))" -ne "$$(wc -c < sim_build/gen_unit_negctl/rtl/generated/fft256.v)" ]; then \
	  echo "NEGATIVE CONTROL FAILED: appended byte is not in the copy only"; exit 1; fi
	@./negctl.sh "perturbed regen copy" "the generator unit tests" "$(GEN_UNIT_NEGCTL_EXPECT)" sim_build/gen_unit_negctl.out -- \
	  env PYTHONPATH=$(CURDIR)/sim_build/gen_unit_negctl $(PYTHON) -m unittest rtl.gen.tests.test_gen.Determinism.test_committed_rtl_matches_fresh_regen

clean:
	rm -rf sim_build results.xml
