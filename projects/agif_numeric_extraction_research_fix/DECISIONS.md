# Decisions

## 2026-03-09
- Decision: Track the numeric extraction rebuild as a dedicated initiative under `projects/agif_numeric_extraction_research_fix/`.
  - Why: Keeps code, data, and paper follow-up organized and separate from unrelated repo outputs.

- Decision: Treat the user-provided Lexware ZIP as a private local invoice holdout, not as public proof.
  - Why: The export is private and currently covers invoices, not the full invoices + receipts research boundary.

- Decision: Fix numeric extraction in the Rust/WASM artifact, not by runner-side post-processing.
  - Why: The benchmark and paper need the real v6 artifact to be correct on its own.

- Decision: Harden A6 so it gates `grand_total`, `tax_total`, `subtotal`, arithmetic consistency, and numeric evidence grounding.
  - Why: The current gate can be passed by patching only one measured field.

- Decision: Use a hybrid data plan: public/open data + synthetic generation for training/benchmark breadth, private local data for local-only validation.
  - Why: This is the safest way to expand coverage without committing private business documents.

- Decision: Replace the old A2/A3 fake scaffold with a deterministic bootstrap learner and a real router-head export.
  - Why: The repo should produce a real fitted artifact for training/export checks instead of writing placeholder bytes.

- Decision: Freeze the strengthened six-case A6 suite as `public_benchmark_v1` until a larger public corpus is curated.
  - Why: This gives the paper an externally checkable benchmark artifact immediately without pretending broader public coverage already exists.

- Decision: Promote the clean `N30` pack at `paper_evidence/2026-03-09/78a1635` to the canonical paper anchor.
  - Why: The clean detached-worktree run passed all target suites with no known gaps, so the paper should stop anchoring claims to the older failing `533c63e` baseline.
