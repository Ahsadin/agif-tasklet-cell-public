# AGIF Paper Evidence Summary

Generated UTC: 2026-03-09T17:22:49Z
Commit: 78a163503ff570407c8c34065a5500c0e34e50d0 (78a1635)
Repetitions: 30

## Release Readiness Results
- Suite: `FINAL_RELEASE_READINESS_SWEEP`
- Pass rate: 100.00% (30/30)
- Determinism rate: 100.00%
- Suite runtime per-repeat latency p50/p95/p99 (ms): 130394.58 / 151537.89 / 152406.03

## Hallucination / Safety Results
- Suite: `review_hallucination_bench_v1`
- Pass rate: 100.00% (30/30)
- Determinism rate: 100.00%
- Final unsafe_allow_count: 0
- Final abstain_accuracy: 1.0
- Final reason_accuracy: 1.0

## Runtime Envelope (A6)
- Suite: `a6_extractor_benchmark_v1`
- Pass rate: 100.00% (30/30)
- Determinism rate: 100.00%
- Suite runtime per-repeat latency p50/p95/p99 (ms): 3516.01 / 3542.79 / 3698.15
- Mean per-case row latency across repeats (ms): 30.69
- Final grand_total_mae: 0.0
- Final tax_total_mae: 0.0
- Final subtotal_mae: 0.0
- Final max_arithmetic_error: 0.0
- Final numeric_grounding_rate: 1.0
- Final abstain_fail_rate: 0.0

## Fail-Closed Negative Test Results
- Suite: `runner_fail_closed_bench_v1`
- Pass rate: 100.00% (30/30)
- Final rejection_rate: 1.0
- Final unsafe_allow_count: 0

## Intelligence Capability Results
- Suite: `reasoning_trace_bench_v1`
- Pass rate: 100.00% (30/30)
- Determinism rate: 100.00%
- Final trace_schema_valid_rate: 1.0
- Final trace_determinism_rate: 1.0
- Final evidence_alignment_rate: 1.0

## Known Gaps
- None observed in this run.

## Raw Artifact Roots
- `FINAL_RELEASE_READINESS_SWEEP`: `paper_evidence/2026-03-09/78a1635/raw/FINAL_RELEASE_READINESS_SWEEP`
- `review_hallucination_bench_v1`: `paper_evidence/2026-03-09/78a1635/raw/review_hallucination_bench_v1`
- `a6_extractor_benchmark_v1`: `paper_evidence/2026-03-09/78a1635/raw/a6_extractor_benchmark_v1`
- `runner_fail_closed_bench_v1`: `paper_evidence/2026-03-09/78a1635/raw/runner_fail_closed_bench_v1`
- `reasoning_trace_bench_v1`: `paper_evidence/2026-03-09/78a1635/raw/reasoning_trace_bench_v1`
