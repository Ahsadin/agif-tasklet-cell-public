# Evidence Table

| Evidence Group | Suite | N | Key Metrics | Pass | Artifact Paths |
|---|---|---:|---|---|---|
| release_readiness | FINAL_RELEASE_READINESS_SWEEP | 30 | target_check_count=20, final_repeat_passed_count=20, final_repeat_failed_ids=[] | Yes | `paper_evidence/2026-03-09/78a1635/raw/FINAL_RELEASE_READINESS_SWEEP` |
| safety_hallucination | review_hallucination_bench_v1 | 30 | unsafe_allow_count=0, abstain_accuracy=1.0, reason_accuracy=1.0, hallucination_resistance_score=1.0 | Yes | `paper_evidence/2026-03-09/78a1635/raw/review_hallucination_bench_v1` |
| runtime_quality_performance | a6_extractor_benchmark_v1 | 30 | routing_accuracy=1.0, currency_accuracy=1.0, vendor_hit_rate=1.0, grand_total_mae=0.0, tax_total_mae=0.0, subtotal_mae=0.0, max_arithmetic_error=0.0, numeric_grounding_rate=1.0, abstain_fail_rate=0.0, determinism_pass_rate=1.0 | Yes | `paper_evidence/2026-03-09/78a1635/raw/a6_extractor_benchmark_v1` |
| fail_closed_tamper_resistance | runner_fail_closed_bench_v1 | 30 | case_count=38, rejection_rate=1.0, unsafe_allow_count=0, expected_reason_match_rate=1.0 | Yes | `paper_evidence/2026-03-09/78a1635/raw/runner_fail_closed_bench_v1` |
| intelligence_capability | reasoning_trace_bench_v1 | 30 | case_count=12, trace_schema_valid_rate=1.0, trace_determinism_rate=1.0, evidence_alignment_rate=1.0 | Yes | `paper_evidence/2026-03-09/78a1635/raw/reasoning_trace_bench_v1` |

## Intelligence Capability Results

- Suite: `reasoning_trace_bench_v1`
- trace_schema_valid_rate: 1.0
- trace_determinism_rate: 1.0
- evidence_alignment_rate: 1.0
