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
- **#158**: Pre-route multi-corner klt sta on the committed gate-level netlist at the three signoff corners (toward T1 item 5)
- **#159**: Produce a klt functional-verification report for the bit-exact FFT suite, on RTL and on the committed gate-level netlist (toward T1 items 5 and 7)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#71**: Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow
- **#158**: Pre-route multi-corner klt sta on the committed gate-level netlist at the three signoff corners (toward T1 item 5)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#178**: verification: drop the Yosys leg from smoke-fft256, check no-macro on the committed synth report

## Proposed

Issues carrying `loom:curated`.

- **#17**: T1 item 2 (layout): klt place-and-route flow and routed GDS for the FFT *(curated)*
- **#71**: Remove the hand-rolled Yosys leg of smoke-fft256: it duplicates the klt synthesize flow *(curated)*
- **#158**: Pre-route multi-corner klt sta on the committed gate-level netlist at the three signoff corners (toward T1 item 5) *(curated)*
- **#159**: Produce a klt functional-verification report for the bit-exact FFT suite, on RTL and on the committed gate-level netlist (toward T1 items 5 and 7) *(curated)*
- **#163**: Post-ruling follow-up to 0006: update the spec growth-schedule row (or land the runner-up swap if ruled otherwise) *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 1 |
| Curated | 5 |
| Architect / Hermit proposals | 0 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
