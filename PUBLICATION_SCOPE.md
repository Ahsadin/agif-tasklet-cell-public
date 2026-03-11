# Publication Scope

This repository is the public research and framework snapshot for AGIF Tasklet
Cell.

## Public In Scope

- framework code and executable artifacts needed to study the offline cell model
- public documentation and research notes
- public benchmark assets for the numeric extraction claim
- the clean paper-evidence anchor at `paper_evidence/2026-03-09/78a1635/`

## Intentionally Excluded

- the private full-product tree
- private holdout data and derived labels
- CellPOS product packaging, licensing, activation, update, and release-readiness artifacts
- large generated ZIP bundles stored directly in git

## License Split

- code and executable artifacts: Apache-2.0
- docs, paper-support text, benchmark notes, and evidence materials: CC BY 4.0
- product and brand names: reserved; no trademark license is granted

## Release Packaging

- The portable clean evidence bundle should be published as a GitHub release
  asset named `agif-paper-evidence-r1-78a1635-clean-n30-portable.zip`.
- The GitHub release for this public repository is the intended software archive
  source for Zenodo.
- Zenodo should archive the public GitHub release, while the portable evidence
  ZIP remains a linked release asset rather than a tracked repo file.
