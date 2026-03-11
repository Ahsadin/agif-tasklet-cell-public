# Decisions

## 2026-03-05

### Decision: Keep existing suite logic and add a separate orchestrator
- Why: Minimize disruption to established checks while producing paper-focused aggregation, repetition, and artifacts.
- Result: Added `tools/paper_eval/run_paper_eval.py` and `tools/paper_eval/run_runner_fail_closed_bench.py`.

### Decision: Keep compatibility defaults for existing scripts, add output overrides
- Why: Existing workflows rely on default behavior.
- Result: Added env/arg overrides for A6 and hallucination scripts so paper-eval writes to `paper_evidence/.../raw/...`.

### Decision: Report failing gates explicitly
- Why: Research evidence must be honest and reproducible.
- Result: `summary.json`/`summary.md` include `known_gaps` (e.g., `grand_total_mae` gate failure).

### Decision: Default repetitions = 30, with make override for practical local runs
- Why: Paper-grade stability needs repeated runs; local validation often needs shorter smoke runs.
- Result: `make paper-eval` defaults to 30 via `PAPER_EVAL_REPETITIONS ?= 30`, and allows override.
