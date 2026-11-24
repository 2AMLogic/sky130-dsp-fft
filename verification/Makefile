# Verification flow for the generated FFT (see README.md). Run from verification/.
# Targets: check-tools lint lint-negctl sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl lint-wrapper fft-bench fft-bench-negctl gen-exact gen-exact-negctl gen-unit gen-unit-negctl fv-reports all clean
PYTHON    ?= ../.venv/bin/python
ROOT      ?= $(abspath ..)
# Repo root on PYTHONPATH: the sim and verification entry points import the
# model as a package (`from sim import ...`) instead of editing sys.path
# themselves, and the cocotb runner hands this process's sys.path to the
# simulator it spawns. A PYTHONPATH set by the caller is kept.
PYPATH     = PYTHONPATH=$(ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))
VERILATOR ?= verilator
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

.PHONY: all check-tools lint lint-negctl lint-wrapper sqnr-ref sqnr-ref-negctl fxp-model fxp-model-negctl smoke-fft256 smoke-fft256-negctl fft-bench fft-bench-negctl gen-exact gen-exact-negctl gen-unit gen-unit-negctl fv-reports fv-reports-force fv-rtl fv-gatelevel fv-negctl clean

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
# the candidate growth-schedule sweep tests, the append-only record-writer tests
# and the per-size model record tests (pure Python + numpy), all five modules
# collected by one unittest invocation.
fxp-model:
	$(PYPATH) $(PYTHON) -m unittest sim.test_fixedpoint_model sim.test_overflow_range sim.test_schedule_sweep sim.test_records sim.test_model_sizes

# Same tests with a flooring rounder; must fail on the convergent-tie check.
fxp-model-negctl:
	@mkdir -p sim_build
	@./negctl.sh "flooring rounder" "the tests" "$(FXP_NEGCTL_EXPECT)" sim_build/fxp_negctl.out -- \
	  env FXP_MUTANT=floor_ties $(PYPATH) $(PYTHON) -m unittest sim.test_fixedpoint_model

# End-to-end smoke of the generated 256-point FFT: regen, Icarus vs the model,
# no-macro check on the committed synth report; appends a record to ../measurements/fft256-smoke.json.
# Tool-version drift is recorded, not fatal (run `make check-tools` for the pins).
smoke-fft256:
	$(PYPATH) $(PYTHON) test_fft256_smoke.py

# One DUT output bit flipped; must fail on the mismatch text and write no record.
smoke-fft256-negctl:
	@mkdir -p sim_build
	@./negctl.sh "perturbed DUT" "the smoke" "$(SMOKE_NEGCTL_EXPECT)" sim_build/smoke_negctl.out -- \
	  env PERTURB=1000 $(PYPATH) $(PYTHON) test_fft256_smoke.py

# Hand-written streaming wrapper (rtl/wrapper): lint it against a port-only stub
# of the generated core (the bit-exact bench is fft-bench).
lint-wrapper:
	$(VERILATOR) --lint-only -Wall -Wno-DECLFILENAME --top-module fft256_stream ../rtl/wrapper/fft256_stream.sv stubs/fft256_stub.sv

# cocotb bench of the streaming wrapper over the generated core: bit-exact vs
# the model on the sim/vectors.py sets, handshake/back-pressure/reset tests.
fft-bench:
	$(PYPATH) $(PYTHON) test_fft256_stream.py

# --- klt functional-verification evidence (issue #159) ----------------------
# The same streaming bench through `klt functional-verification`, three times:
# on the RTL sources, on the committed gate-level netlist (zero-delay: no SDF
# block, so the report's environment.sdf is null), and a negative control with
# one output bit flipped (FFT_BENCH_PERTURB, as fft-bench-negctl seeds it).
# The committed reports are the T1 item 5 functional artifacts, uncited in
# manifests/sky130-dsp-fft.json pending spec ratification (see README.md).
# Manual, like smoke-fft256: the gate-level leg alone interprets ~130k cycles
# of sky130 UDP cell models and takes roughly two hours on the pinned Icarus.
# klt pin: the lowest released klayout-tools whose functional-verification
# runs this bench is 0.9.0 -- the bench needs request.env (klayout-tools
# #4338) both for the negative control's stimulus and so the bench's own
# PYTHONPATH bootstrap (Runner propagates the caller's sys.path) reaches the
# sim/ package; 0.8.0 has no request.env. uvx supplies klt with its cocotb
# extra; the two --with pins hold cocotb and numpy at toolchain.json's
# versions in the bench process.
KLT_FV_VERSION ?= 0.9.0
KLT_FV = $(PYPATH) uvx --from "klayout-tools[functional-verification]==$(KLT_FV_VERSION)" \
  --with cocotb==2.1.0 --with numpy==2.3.4 klt functional-verification
PDK_VERILOG_DIR = $(PDK_ROOT)/ciel/sky130/versions/$(shell $(PYTHON) -c "import json; print(json.load(open('toolchain.json'))['pdk']['revision'])")/sky130A/libs.ref/sky130_fd_sc_hd/verilog
PDK_HD_VERILOG = sim_build/pdk-verilog/primitives.v sim_build/pdk-verilog/sky130_fd_sc_hd.v
RTL_SOURCES = ../rtl/wrapper/fft256_stream.sv $(sort $(wildcard ../rtl/generated/*.v))
BENCH_INPUTS = test_fft256_stream.py ../rtl/params/fft256.params ../sim/__init__.py \
  ../sim/fixedpoint_model.py ../sim/vectors.py
# The gate-level request sources the sky130_fd_sc_hd Verilog cell models from
# the pinned ciel PDK revision (toolchain.json), materialised under
# sim_build/ so the committed request carries only repo-relative paths.
$(PDK_HD_VERILOG): sim_build/pdk-verilog/%.v: $(PDK_VERILOG_DIR)/%.v
	@mkdir -p sim_build/pdk-verilog
	cp $< $@

reports:
	mkdir -p reports

fv-reports: fv-rtl fv-gatelevel fv-negctl

fv-rtl: reports/fv-rtl.report.json
fv-gatelevel: reports/fv-gatelevel.report.json
fv-negctl: reports/fv-negctl.report.json

# Each report is generated into a temporary file and moved over the committed
# one only after the run meets that leg's success criterion, so a failed or
# interrupted run never leaves an empty or partial report behind. The reports
# are committed evidence, so the file targets below skip when the file is newer
# than its inputs; `make fv-reports-force` (or `make -B fv-reports`) always
# re-runs all three simulations.
fv-reports-force:
	$(MAKE) -B fv-reports

reports/fv-rtl.report.json: fv_rtl.request.json $(BENCH_INPUTS) $(RTL_SOURCES) | reports
	@rm -f $@.tmp
	@if $(KLT_FV) -o sim_build/fv-rtl --format json $< > $@.tmp; then mv $@.tmp $@; \
	else echo "fv-rtl FAILED: committed report left untouched"; rm -f $@.tmp; exit 1; fi

reports/fv-gatelevel.report.json: fv_gatelevel.request.json $(BENCH_INPUTS) $(PDK_HD_VERILOG) ../netlist/fft256_stream.sky130_fd_sc_hd.v | reports
	@rm -f $@.tmp
	@if $(KLT_FV) -o sim_build/fv-gatelevel --format json $< > $@.tmp; then mv $@.tmp $@; \
	else echo "fv-gatelevel FAILED: committed report left untouched"; rm -f $@.tmp; exit 1; fi

# The perturbed run must fail, and its report must carry the mismatch text and
# the stimulus (environment.env.FFT_BENCH_PERTURB), so a request error or a
# crash cannot count as "caught" -- the same contract negctl.sh holds the other
# negative controls to, asserted on the JSON. The committed report is replaced
# only once the temporary one passes that assertion.
reports/fv-negctl.report.json: fv_negctl.request.json $(BENCH_INPUTS) $(RTL_SOURCES) | reports
	@rm -f $@.tmp
	@if $(KLT_FV) -o sim_build/fv-negctl --format json $< > $@.tmp; then \
	  echo "NEGATIVE CONTROL FAILED: perturbed run passed (committed report left untouched)"; rm -f $@.tmp; exit 1; fi
	@if ! $(PYTHON) -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["status"]=="fail", "report status is not fail"; ts=r["tests"]; assert any(t["status"]=="failed" and "stream output differs from bit-accurate model" in (t.get("error_message") or "") for t in ts), "no failed test carries the mismatch text"; assert r["environment"]["env"].get("FFT_BENCH_PERTURB")=="1000", "report does not record the perturbation stimulus"' $@.tmp; then \
	  echo "NEGATIVE CONTROL FAILED: report does not record the expected failure (committed report left untouched)"; rm -f $@.tmp; exit 1; \
	else mv $@.tmp $@; echo "negative control OK: perturbed run caught, report records the mismatch and stimulus"; fi

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
# so the copy shadows it). The clean copy must pass first, so a copy-induced
# difference (a path-dependent regen input, a file cp skips) cannot make the
# committed-vs-regen check fail for a reason other than the appended byte; the
# perturbed copy must then fail AND carry GEN_UNIT_NEGCTL_EXPECT, so a missing
# file or crash does not count as "caught". rtl/generated itself is never
# modified.
gen-unit-negctl:
	@rm -rf sim_build/gen_unit_negctl
	@mkdir -p sim_build/gen_unit_negctl
	@cp -r ../rtl sim_build/gen_unit_negctl/rtl
	@if ! env PYTHONPATH=$(CURDIR)/sim_build/gen_unit_negctl $(PYTHON) -m unittest \
	      rtl.gen.tests.test_gen.Determinism.test_committed_rtl_matches_fresh_regen \
	      > sim_build/gen_unit_negctl_clean.out 2>&1; then \
	  echo "NEGATIVE CONTROL FAILED: clean copy of the rtl tree does not pass the committed-vs-regen check (see sim_build/gen_unit_negctl_clean.out)"; exit 1; fi
	@printf 'x' >> sim_build/gen_unit_negctl/rtl/generated/fft256.v
	@if [ "$$(( $$(wc -c < ../rtl/generated/fft256.v) + 1 ))" -ne "$$(wc -c < sim_build/gen_unit_negctl/rtl/generated/fft256.v)" ]; then \
	  echo "NEGATIVE CONTROL FAILED: appended byte is not in the copy only"; exit 1; fi
	@./negctl.sh "perturbed regen copy" "the generator unit tests" "$(GEN_UNIT_NEGCTL_EXPECT)" sim_build/gen_unit_negctl.out -- \
	  env PYTHONPATH=$(CURDIR)/sim_build/gen_unit_negctl $(PYTHON) -m unittest rtl.gen.tests.test_gen.Determinism.test_committed_rtl_matches_fresh_regen

clean:
	rm -rf sim_build results.xml
