# AGIF Paper Evidence R1

## Goal
Preserve the clean, paper-grade empirical evidence anchor for Whitepaper R1 and
document how it should be published alongside the public research repo.

## Scope
- Canonical in-repo anchor: `paper_evidence/2026-03-09/78a1635/`
- Portable release-bundle filename: `agif-paper-evidence-r1-78a1635-clean-n30-portable.zip`
- Evidence suites:
  - `FINAL_RELEASE_READINESS_SWEEP`
  - `review_hallucination_bench_v1`
  - `a6_extractor_benchmark_v1`
  - `runner_fail_closed_bench_v1`
- `reasoning_trace_bench_v1`

## Verification
Check that the public anchor contains:

- `paper_evidence/<date>/<sha>/env.json`
- `paper_evidence/<date>/<sha>/raw/...`
- `paper_evidence/<date>/<sha>/summary.json`
- `paper_evidence/<date>/<sha>/summary.md`
- `paper_evidence/<date>/<sha>/paper_table.md`
- `paper_evidence/<date>/<sha>/reproduce.md`
- `paper_evidence/<date>/<sha>/figures/*.png` (generated PNG figures)

The committed folder and the portable ZIP are audit/results bundles. This public
repo preserves the clean recorded anchor; it does not ship the full private
generation harness that originally produced the bundle.

## Known gap handling
If any gate fails, it is reported in `summary.json` and `summary.md` under `known_gaps` (not hidden).
