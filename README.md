# AGIF Tasklet Cell

AGIF Tasklet Cell is a public research snapshot for verifier-backed offline AI artifacts in native applications. This repository preserves the core framework code, cell bundles, public benchmark assets, and the clean paper-evidence anchor used by the AGIF whitepaper.

This public snapshot does not include private CellPOS product code, packaging, licensing flows, update flows, or private business-data validation assets.

## Included

- cell bundles under `cells/`
- runner scaffold under `runner/`
- intelligence source under `intelligence/`
- examples and public fixtures under `examples/` and `fixtures/`
- architecture and contract docs under `docs/`
- clean paper-evidence anchor under `paper_evidence/2026-03-09/78a1635/`
- public benchmark support assets under `projects/agif_numeric_extraction_research_fix/`

## Not Included

- the private full-product tree
- CellPOS product packaging, licensing, activation, and update artifacts
- private holdout data and private derived labels
- generated ZIP bundles tracked in git
- internal working notes that were only useful inside the private prep repo

## Evidence And Publication

- Software archive DOI: [10.5281/zenodo.18950210](https://doi.org/10.5281/zenodo.18950210)
- Paper DOI: [10.5281/zenodo.18946355](https://doi.org/10.5281/zenodo.18946355)
- Canonical clean evidence anchor: `paper_evidence/2026-03-09/78a1635/`
- Portable bundle filename for release publishing: `agif-paper-evidence-r1-78a1635-clean-n30-portable.zip`
- Public evidence release: [paper-evidence-r1-78a1635-clean](https://github.com/Ahsadin/agif-tasklet-cell-public/releases/tag/paper-evidence-r1-78a1635-clean)
- The portable bundle is intentionally distributed as a GitHub release asset, not committed into git.
- The committed evidence tree is an audit/results record. It is not a self-contained rerun environment.

For the paper-support bundle details, see `docs/PAPER_EVIDENCE_R1.md`.

## License Matrix

- Code and executable artifacts in this repository are licensed under Apache-2.0. See `LICENSE`.
- Documentation, paper-support text, benchmark notes, and evidence materials are licensed under CC BY 4.0. See `LICENSE-docs`.
- `CellPOS`, `ENFSystems`, and related names and logos are reserved. See `TRADEMARKS.md`.

## Public Scope

This repository is the public research/core snapshot. Sellable product pieces remain private or separately licensed. See `PUBLICATION_SCOPE.md` for the release boundary that should be used for GitHub publication and Zenodo archiving.
