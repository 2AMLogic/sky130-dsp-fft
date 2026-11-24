# 0007 — Storage evidence: cite the committed synthesis report

- **Status**: Proposed. Agents do not ratify it.
- **Date**: 2026-11-24
- **Scope**: the Status cell of the Storage row in `spec/spec.md` (`:40` at
  `origin/main` @ `f5c5c27`). That cell cites "no macros" in the netlist the
  retired smoke Yosys leg used to synthesize — an artifact that no longer
  exists: the 2026-11-23 operator ruling on #71 (option `a`) removed that
  leg of `make smoke-fft256`, landed as PR #178 (merged `b6d7dd0`), so the
  smoke run no longer produces a netlist at all. This record re-bases the
  cell's citation on the committed `synth/fft256.synth.report.json`. One
  cell of one row changes; no Target, Fallback, Stretch or
  Verification-method cell is edited.
- **Numbering**: re-checked at write time on `feature/issue-179` (branched
  from `origin/main` @ `f5c5c27`, re-verified after rebasing onto `4acb60a`
  when #190 landed mid-flight): `spec/decisions/` holds 0001-0006, and no
  open or just-merged PR (#166 open, #190 `4acb60a`) touches
  `spec/decisions/` (`gh pr diff --name-only`), so 0007 is the next free
  number. Open PR #166 edits `spec/spec.md` near the Clock row (`:38`); if
  it lands first, the Storage row's line number shifts and this record's
  `:40` reference is re-derived, not the other way round.
- **Not changed**: the v1 flop-storage requirement and the no-SRAM
  verification method (0003; the Storage row's Target/Fallback/Stretch
  and Verification-method cells), records 0001-0006 (append-only), the
  smoke test, the RTL, the netlist, `synth/` and `measurements/`. The
  other smoke-citing rows (`spec/spec.md:22`, `:29`, `:30` — bit-exactness,
  overflow, simulated SQNR on `measurements/fft256-smoke.json`) keep their
  citations: PR #178 kept those legs of the smoke run.

## What moved, and why

The row's verdict — flop storage, no SRAM macros — was evidenced by the
smoke test's Yosys leg, which synthesized the bare generated core (top
`fft256`) ad hoc on every smoke run and asserted the mapped netlist held
no macros. #71's ruling rejected that arrangement on two grounds: it was
a second synthesis flow drifting next to the `klt synthesize` flow that
produces the committed netlist (different script, different top, different
numbers — 61525 cells for the discarded smoke-flow netlist against 60715
for the committed one, wrapper included), and the netlist it checked was
discarded, so the figure described a netlist nobody could inspect. Option
`a` moved the no-macro assertion onto the committed report:
`verification/test_fft256_smoke.py:121-128` (`check_no_macros()`) now
reads `synth/fft256.synth.report.json` and exits non-zero on any macro
instance or any cell type outside `sky130_fd_sc_hd__*`.

The committed report is the stronger source on every axis that mattered:

| | Retired smoke Yosys leg | Committed report |
|---|---|---|
| Top | `fft256` (bare generated core) | `fft256_stream` (wrapper over the core, the top that goes to place-and-route) |
| Netlist | discarded (`sim_build/` stat JSON only) | committed (`netlist/fft256_stream.sky130_fd_sc_hd.v`, keyed by the report's `netlist_sha256`) |
| Freshness | none; two ad-hoc records (2026-10-30, 2026-11-15), neither re-checked | asserted on every smoke run by `check_no_macros()`; `klt synthesize --check` freshness in the T1 item 1 attestation |

## The evidence, and its limits

Static reads of the committed artifacts, re-verified 2026-11-24 on
`feature/issue-179` (at the `f5c5c27` branch point and again after the
rebase onto `4acb60a`; the artifacts are identical):

- `synth/fft256.synth.report.json`: `hdl_toplevel == "fft256_stream"`,
  `macro_instance_count == 0`, `instance_counts_by_type` holds 151 keys,
  all `sky130_fd_sc_hd__*`, summing to 60715 instances; synthesized at the
  `sky130_fd_sc_hd__tt_025C_1v80` deck (open_pdks `f6eeac7d…`).
- The report's `netlist_sha256`
  (`5a441dc7fa126fbde406230b6f2e489f38d1a288bf9db2a2c649d577dac32185`)
  matches `sha256sum netlist/fft256_stream.sky130_fd_sc_hd.v`.

Limits, stated plainly: this is synthesis-mapping evidence, not a
measurement and not silicon. The macro count is corner-independent (a
macro instance would appear in `macro_instance_count` whatever deck
mapped the netlist), so the single `tt_025C_1v80` deck is not a gap for
*this* row. No timing claim is made here — timing is the Clock row's
business, and the report's own `sta_unavailable_reason` records why its
`sta` leg is unpopulated. The check is structural, which is exactly the
method the row's Verification-method cell names ("no SRAM macros in the
netlist"), now applied to the committed netlist's report instead of a
discarded one.

## Decision

**The Storage row's Status cell becomes: "evidenced (flop storage, zero
SRAM macros in the [committed FFT256 synthesis
report](../synth/fft256.synth.report.json))".** The verdict is unchanged;
only its citation moves, from a retired producer to the committed,
hash-keyed artifact that place-and-route (#17) actually consumes. Storage
stays flops for v1 and compiled SRAM stays out of scope (0003); the
row's Verification-method cell ("no SRAM macros in the netlist") is
untouched — `check_no_macros()` is that method, enforced.

Rejected alternatives:

- *Edit `spec/spec.md` without a decision record*: violates `CLAUDE.md`
  ("Spec changes go through `spec/` with a decision record") and the
  explicit scope requirement in #71 and #179.
- *Amend `spec/decisions/0003-timing-and-storage.md` in place*:
  rejected — `spec/README.md` mandates append-only records ("a change is
  a new record that supersedes the old one").

## Consequences and open questions

1. The spec's Storage citation is now a committed artifact whose content
   the smoke test asserts on every run, so the citation cannot go stale
   silently: a regenerated report with macros fails
   `make -C verification smoke-fft256`.
2. 0003's flop estimate and its storage ruling are untouched; this record
   supersedes only the *evidence citation* in the Status cell, not the
   requirement.
3. The smoke records in `measurements/fft256-smoke.json` are
   append-only history and keep their Yosys-leg fields; nothing there is
   rewritten.

## Citations

| Id | What it establishes | Status |
|---|---|---|
| `synth/fft256.synth.report.json` | the evidence: top `fft256_stream`, `macro_instance_count` 0, 151 `sky130_fd_sc_hd__*` cell types over 60715 instances at `tt_025C_1v80`; `netlist_sha256` keys it to the committed netlist | committed |
| `netlist/fft256_stream.sky130_fd_sc_hd.v` | the committed netlist; sha256 matches the report's `netlist_sha256` (re-verified 2026-11-24) | committed |
| `verification/test_fft256_smoke.py:121-128` | `check_no_macros()`: reads the report, exits non-zero on macros or non-`sky130_fd_sc_hd__` cells — the enforcement behind the new citation | committed |
| #71 | the 2026-11-23 operator ruling (option `a`): remove the smoke Yosys leg, move the no-macro check onto the committed report; names this spec follow-up as the cost | ruled |
| PR #178 | landed option `a` on `main` (merged `b6d7dd0`, 2026-11-24) | merged |
| `spec/decisions/0003-timing-and-storage.md` | storage is flops for v1; compiled SRAM out of scope — the requirement this row carries | committed |
| `measurements/fft256-smoke.json` | the smoke record the row's sibling citations (`:22`, `:29`, `:30`) rest on; unchanged | committed |
