# AGENTS.override.md (Numeric Extraction Research Fix)

## Scope
- This initiative covers the v6 numeric extraction rebuild, benchmark hardening, private/public evidence setup, and paper claim alignment.

## Canonical outputs
- Keep initiative planning, manifests, and verification notes under `projects/agif_numeric_extraction_research_fix/`.
- Keep private source documents outside Git. Commit only manifests, hashes, redacted samples, and summary reports.

## Data handling
- Treat user-provided Lexware exports as local-only validation inputs.
- Do not copy private PDFs/XML exports into the repository.
- Public/open data must record source URL, license note, and retrieval date before use in benchmarks.

## Claim boundary
- Default research claim boundary is invoices + receipts for `en-US`, `de-DE`, and `es-ES`.
- If private validation only covers invoices, paper text must say so explicitly.

## Reporting rule
- Never present locally verified private evidence as public proof.
