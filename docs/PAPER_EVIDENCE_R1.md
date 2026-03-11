# Paper Evidence R1

This document indexes the public proof package for Whitepaper R1.

- Canonical clean commit SHA: `78a1635`
- Canonical in-repo evidence path: `paper_evidence/2026-03-09/78a1635`
- Portable release-bundle filename: `agif-paper-evidence-r1-78a1635-clean-n30-portable.zip`
- Publication note: publish the portable bundle as a GitHub release asset beside the public software release; it is intentionally not tracked in git.

## Suite Overview

- `FINAL_RELEASE_READINESS_SWEEP`: end-to-end release readiness checks across the baseline product surface.
- `review_hallucination_bench_v1`: abstention and reason-quality benchmark for hallucination resistance.
- `a6_extractor_benchmark_v1`: runtime quality and performance benchmark for the A6 extractor path.
- `runner_fail_closed_bench_v1`: negative-case fail-closed and tamper-resistance benchmark for the runner and cell bundle.
- `reasoning_trace_bench_v1`: structured reasoning-trace benchmark validating schema, determinism, and evidence alignment.

## Known Gap

- Canonical clean anchor `78a1635`: no known gaps in the generated `N30` pack.
- Historical baseline at `533c63e`: `A6 gate failed: grand_total_mae` and the recorded environment was captured from a dirty working tree.

## Key Results

- `FINAL_RELEASE_READINESS_SWEEP`: `30/30` pass, `20/20` target checks passed in the final repeat.
- `a6_extractor_benchmark_v1`: `30/30` pass with `grand_total_mae = 0.0`, `tax_total_mae = 0.0`, `subtotal_mae = 0.0`, `numeric_grounding_rate = 1.0`, and `abstain_fail_rate = 0.0`.
- `review_hallucination_bench_v1`: `30/30` pass with `unsafe_allow_count = 0`.
- `runner_fail_closed_bench_v1`: `30/30` pass with `rejection_rate = 1.0`.
- `reasoning_trace_bench_v1`: `30/30` pass with schema validity, determinism, and evidence alignment all at `1.0`.

## Key Files

- `summary.md`
- `paper_table.md`
- `summary.json`
- `env.json`
- `figures/` (generated PNG figures)

`summary.md` and `paper_table.md` are the citation-oriented outputs for the
paper. Raw artifacts remain in the evidence tree for audit of the recorded run.

The committed evidence tree and the portable ZIP are audit/results bundles. This
public repository preserves the clean recorded anchor, but it does not ship the
full private generation harness that originally produced the bundle. The public
release should therefore present the evidence as a recorded audit artifact, not
as a standalone rerun environment.
