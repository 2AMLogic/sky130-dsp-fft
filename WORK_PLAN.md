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
- **#76**: Sweep candidate growth schedules in the fixed-point model and record SQNR and overflow per candidate

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#79**: README Reproduce table names superseded item 10 attestation -3; point it at the live one
- **#80**: Retire the hand-rolled sys.path bootstraps: run sim and generator entry points as modules
- **#81**: Collapse the four copy-pasted negative-control recipes in verification/Makefile into one helper

## In Progress

Issues currently being built (`loom:building`).

- **#78**: Survey FIR sources and write decision record 0005 (Proposed)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#17**: T1 item 2 (layout): klt place-and-route flow and routed GDS for the FFT *(curated)*
- **#76**: Sweep candidate growth schedules in the fixed-point model and record SQNR and overflow per candidate *(curated)*
- **#77**: Record model SQNR and overflow for the 64-point fallback and 1024-point stretch sizes *(curated)*
- **#78**: Survey FIR sources and write decision record 0005 (Proposed) *(curated)*
- **#79**: README Reproduce table names superseded item 10 attestation -3; point it at the live one *(curated)*

## Proposed (Architect / Hermit)

- **#71**: Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 4 |
| Ready (`loom:issue`) | 3 |
| In Progress (`loom:building`) | 1 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 5 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
