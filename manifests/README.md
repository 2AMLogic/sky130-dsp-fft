# Block manifest and tier-verdict record

This directory holds this block's `klt signoff` input and its committed
output, so the T1 state is graded by
[`klt signoff`](https://github.com/2AMLogic/klayout-tools/blob/main/docs/cli/signoff.md)
rather than read by hand.

## Files

- **`sky130-dsp-fft.json`**: the block manifest. `block: sky130-dsp-fft`,
  `kind: digital`, and an `evidence` map that is deliberately empty: no T1
  item is cited yet. Citations are added one item at a time as artifacts
  land, each pinning the `content_hash` of the artifact it cites.
- **`design-evidence-tiers.md`**: the T1-T4 checklist the grader parses.
  Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@44cc42323184`](https://github.com/2AMLogic/klayout-tools/blob/44cc42323184a2f3a440b89789bf174488a6b1e4/docs/design-evidence-tiers.md)
  (`docs/design-evidence-tiers.md`; upstream is MIT-licensed, and this
  repo's Apache-2.0 `LICENSE` does not relicense the vendored copy). To
  re-vendor, copy the file from a named upstream commit, update the commit
  here, and regenerate the record in the same PR.
- **`sky130-dsp-fft.signoff.json`**: **the verdict of record**, the committed
  output of the command below. Never hand-edit it.

## Regenerate

```console
uvx --from "klayout-tools==0.8.0" klt signoff \
    --manifest manifests/sky130-dsp-fft.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/sky130-dsp-fft.signoff.json
```

Item 10 is cited from an attestation envelope generated from
`item10-inventory.json` (generate, then re-grade; run `--check` last, since any
edit to the inventory or an inventoried file changes the recorded hashes):

```console
uvx --from "klayout-tools==0.8.0" klt signoff --attest 10 \
    --inventory manifests/item10-inventory.json \
    -o manifests/item10-attestation.json
uvx --from "klayout-tools==0.8.0" klt signoff --attest 10 \
    --inventory manifests/item10-inventory.json \
    --check manifests/item10-attestation.json
```

`klt signoff --manifest` exits `3` when at least one T1 item is `unmet` (a
valid, clean run) and `0` when every item is `met`. Any change that affects
the verdict (new evidence, a manifest edit, a vendored-doc bump, a `klt` pin
bump) regenerates and commits the record in the same PR. The pin appears in
this file and in `.github/workflows/signoff.yml`; change both together.

## Freshness is CI-enforced

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml) re-runs the
command above on every push to `main` and every pull request, and
byte-compares the fresh output against the committed record. A manifest
change without a regenerated record fails the build.

## Current verdict

Not-T1: `tier` is `null` and all 11 T1 items are `unmet`, each with a stated
reason in `sky130-dsp-fft.signoff.json`.
