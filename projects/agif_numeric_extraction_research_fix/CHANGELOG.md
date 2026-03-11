# Changelog

## 2026-03-10
- Clarified the manuscript updater wording so the clean anchor is described as a portable audit/results bundle rather than a self-contained rerun pack.
- Updated the manuscript updater for the A6 latency labeling split between suite runtime and per-case row latency.
- Updated the manuscript updater to distinguish repository-recorded CellPOS artifact evidence from independent inspection of the tarball itself.

## 2026-03-09
- Cleaned stale repo-level paper references in:
  - `README.md`
  - `RELEASE_INSTRUCTIONS.md`
- Hardened the manuscript updater so it also rewrites the remaining stale A6 failure section and appendix baseline metadata in the latest R4 manuscript.
- Re-synced the latest local manuscript to the clean `78a1635` anchor while keeping `533c63e` as historical baseline context only.
- Created initiative workspace `projects/agif_numeric_extraction_research_fix/`.
- Added initiative source-of-truth files:
  - `projects/agif_numeric_extraction_research_fix/AGENTS.override.md`
  - `projects/agif_numeric_extraction_research_fix/PROJECT_README.md`
  - `projects/agif_numeric_extraction_research_fix/DECISIONS.md`
  - `projects/agif_numeric_extraction_research_fix/CHANGELOG.md`
- Locked initial execution direction:
  - private Lexware ZIP is invoice-focused local holdout v1
  - public/open data will cover receipts and extra locale breadth
  - real fix must land in Rust/WASM, not in runner post-processing
- Replaced the placeholder numeric extraction logic in `intelligence/wasm/src/lib.rs` with grounded candidate scoring, arithmetic reconciliation, evidence refs, and abstention output.
- Removed the v6 runner-side post-processing patch from `runner/cell`.
- Strengthened A6 benchmark inputs and gates to score `grand_total`, `tax_total`, `subtotal`, arithmetic consistency, abstain policy, and numeric evidence grounding.
- Added local/private and public/open data scaffolding:
  - `04_execution/data/summarize_lexware_holdout.py`
  - `04_execution/data/generate_synthetic_numeric_dataset.py`
  - `07_assets/public_sources/source_manifest.json`
- Generated local-only holdout summary outputs:
  - `06_outputs/private_holdout/lexware_2025-08_2025-12_summary.json`
  - `06_outputs/private_holdout/lexware_2025-08_2025-12_summary.md`
- Generated a synthetic dataset sample at:
  - `07_assets/synthetic/sample_numeric_v1/`
- Replaced the old A2/A3 placeholder scaffold with a deterministic learned routing/export path in the paired private prep repo.
- Added private/public benchmark support assets:
  - `04_execution/data/build_lexware_holdout_labels.py`
  - `07_assets/public_benchmark_v1/README.md`
  - `07_assets/public_benchmark_v1/manifest.json`
- Added repeatable manuscript update tooling:
  - `04_execution/paper/update_r3_manuscript.py`
- Updated the paired paper-evidence summary tooling so the paper summary reports the strengthened A6 metrics instead of only `grand_total_mae`.
- Completed the clean `N30` paper-evidence anchor for commit `78a1635` and copied it into:
  - `paper_evidence/2026-03-09/78a1635/`
- Updated the repo paper evidence index to point to the clean `78a1635` anchor and record the final strengthened A6 results.
- Updated the private manuscript working copy outside this repository.
- Render-checked the updated manuscript in the private prep workspace.
- Expanded the manuscript updater so it also rewrites leftover old-A6-failure wording in the readiness discussion and appendix evidence excerpts.
