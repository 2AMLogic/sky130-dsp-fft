# Work Plan

Prioritized roadmap from current GitHub label state.
Maintained by the Guide triage role; the region between the markers is generated.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#17**: T1 item 2 (layout): klt place-and-route flow and routed GDS for the FFT

## Important

`loom:important`; taken before unlabelled work.

- **#18**: T1 item 3 (DRC clean): klt drc on the routed FFT GDS with coverage disclosed
- **#19**: T1 item 4 (LVS clean): klt lvs of the routed FFT vs the gate-level netlist
- **#20**: T1 item 11 (power delivery): klt erc supply spec and PDN evidence for the routed FFT

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#86**: Collapse the three copy-pasted test runners in sim/ onto unittest, the repo's attested runner
- **#90**: Retire the loose-tolerance DFT in the generator's smoke test: the bit-accurate model it waited on now exists

## In Progress

Issues currently being built (`loom:building`).

- **#77**: Record model SQNR and overflow for the 64-point fallback and 1024-point stretch sizes
- **#81**: Collapse the four copy-pasted negative-control recipes in verification/Makefile into one helper
- **#88**: Derive the overflow sweep's vector kinds from VECTOR_SETS instead of restating the seeds
- **#89**: Narrow the generator's stage_widths cap from 40 to 32: widths above 32 have no reference model
- **#91**: test_gen.py documents a unittest discover command that does not run
- **#92**: Consolidate the three copy-pasted SQNR/overflow scoring paths onto one helper
- **#94**: Consolidate the three copy-pasted append-only record writers; the untested one feeds committed evidence

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#95**: refactor(verification): single-source the negctl must-fail contract in negctl.sh
- **#99**: refactor: derive the overflow sweep's vector kinds from VECTOR_SETS

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#75**: docs: roadmap as of 2026-11-13
- **#98**: docs: fix two documented Python invocations in rtl/ that do not run

## Proposed

Issues carrying `loom:curated`.

- **#17**: T1 item 2 (layout): klt place-and-route flow and routed GDS for the FFT *(curated)*
- **#77**: Record model SQNR and overflow for the 64-point fallback and 1024-point stretch sizes *(curated)*
- **#90**: Retire the loose-tolerance DFT in the generator's smoke test: the bit-accurate model it waited on now exists *(curated)*
- **#91**: test_gen.py documents a unittest discover command that does not run *(curated)*

## Proposed (Architect / Hermit)

- **#71**: Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 7 |
| PRs awaiting review | 2 |
| Approved PRs awaiting merge | 2 |
| Curated | 4 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
