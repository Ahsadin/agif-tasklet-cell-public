# AGIF Numeric Extraction Research Fix

## Goal
Replace the placeholder v6 numeric extraction logic with a grounded extractor that can separate totals, tax, subtotal, invoice IDs, and other distractors across invoices and receipts.

## Scope
- In scope:
  - `intelligence/wasm/src/lib.rs`
  - `runner/cell` v6 post-processing removal
  - A6 benchmark hardening
  - research data/training scaffolding for public and private evaluation
  - paper evidence alignment for the A6 claim
- Out of scope:
  - unrelated v1-v5 refactors
  - committing private business documents
  - broad claims outside invoices + receipts

## Current inputs
- Private local holdout v1:
  - retained outside this public repo
  - any validation against it is locally verified only
- Public/open side:
  - source tracking and license notes recorded in `07_assets/public_sources/`
  - current frozen public benchmark seed recorded in `07_assets/public_benchmark_v1/`
- Synthetic side:
  - deterministic sample shipped under `07_assets/synthetic/`

## Execution plan
1. Replace placeholder numeric logic in the v6 Rust/WASM extractor.
2. Remove the Python runner post-processing patch so the artifact itself is correct.
3. Strengthen A6 to require grounded `grand_total`, `tax_total`, `subtotal`, and arithmetic consistency.
4. Add deterministic data/training/export scaffolding for public and private evaluation.
5. Regenerate evidence and update paper support text with honest claim boundaries.

## Verification target
- `cargo test --manifest-path intelligence/wasm/Cargo.toml`
- inspect `07_assets/public_benchmark_v1/`
- inspect `paper_evidence/2026-03-09/78a1635/`

## Notes
- Private holdout files remain outside Git.
- Local-only derived labels from private exports should be written outside Git or into ignored output folders.
- Public benchmark and synthetic seed artifacts shipped in this public repo live under `projects/agif_numeric_extraction_research_fix/07_assets/`.
- Manuscript working files remain outside this repository.
