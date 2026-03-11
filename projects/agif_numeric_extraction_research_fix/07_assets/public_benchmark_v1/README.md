# Public Benchmark v1

This folder is the public, repo-committed benchmark reference for the numeric extraction claim.

## Scope
- invoices + receipts
- `en-US`, `de-DE`, `es-ES`
- numeric fields:
  - `grand_total`
  - `tax_total`
  - `subtotal`

## Source of truth
- Cases: `projects/agif_numeric_extraction_research_fix/07_assets/public_benchmark_v1/cases.json`
- Gate config: `projects/agif_numeric_extraction_research_fix/07_assets/public_benchmark_v1/gate_config.json`
- Manifest: `projects/agif_numeric_extraction_research_fix/07_assets/public_benchmark_v1/manifest.json`

## Why this exists
- It gives the paper a public, externally checkable benchmark artifact.
- It keeps the public proof separate from the private Lexware holdout.
- It matches the strengthened A6 gate used by the local verification path.

## Limits
- This is the current frozen public seed benchmark, not the final broad public corpus.
- Private local validation still remains separate and must be described as locally verified only.
