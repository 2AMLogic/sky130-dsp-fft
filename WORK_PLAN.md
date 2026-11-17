# Work Plan

Prioritized roadmap from current GitHub label state.
Maintained by the Guide triage role; the region between the markers is generated.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#132**: test(sim): dual drift guard names both red causes and derives the all-ceiling keys
- **#137**: fix: route the smoke record's SQNR through json_safe and reject non-finite records at the shared writer
- **#145**: chore(loom): resync installed Loom to v0.19.1305

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

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#127**: Drift-guard dual test tells a maintainer to fix the probe when the generator is genuinely narrower
- **#135**: verification/test_fft256_smoke.py writes a bare Infinity literal for an exact-match SQNR, bypassing the json_safe convention

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#132**: test(sim): dual drift guard names both red causes and derives the all-ceiling keys
- **#137**: fix: route the smoke record's SQNR through json_safe and reject non-finite records at the shared writer
- **#145**: chore(loom): resync installed Loom to v0.19.1305

## Proposed

Issues carrying `loom:curated`.

- **#17**: T1 item 2 (layout): klt place-and-route flow and routed GDS for the FFT *(curated)*
- **#127**: Drift-guard dual test tells a maintainer to fix the probe when the generator is genuinely narrower *(curated)*
- **#135**: verification/test_fft256_smoke.py writes a bare Infinity literal for an exact-match SQNR, bypassing the json_safe convention *(curated)*

## Proposed (Architect / Hermit)

- **#71**: Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 3 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 3 |
| Curated | 3 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
