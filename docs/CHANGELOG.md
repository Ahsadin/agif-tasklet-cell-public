# Changelog

## 2026-03-01

- Closed `ISSUE-079` by publishing `docs/SNAPSHOTS/PHASE6_SUMMARY_2026-03-01.md`, marking Phase 6 as `CLOSED` across `docs/05_PHASE_PLAN.md`, `docs/ISSUES_INDEX.md`, and `docs/PHASE_MAP.md`, and explicitly linking successful Prototype Proof Gate evidence in `docs/SNAPSHOTS/PHASE6_PROTOTYPE_EVIDENCE_2026-03-01.md`.
- Closed `ISSUE-078` by publishing `docs/SNAPSHOTS/PHASE6_PROTOTYPE_EVIDENCE_2026-03-01.md` with executable command traceability from `scripts/demo_phase6.sh`, captured `stdout`/`stderr` evidence, replay `result_hash` + tolerance decisions, and explicit generated artifact file paths.
- Closed `ISSUE-077` by adding one-command runbook script `scripts/demo_phase6.sh` that executes extractor/validators/replay/learning gates, exits non-zero on any gate failure, and emits machine-greppable final summary (`PHASE6_PROTOTYPE_PASS SUMMARY ...` or `PHASE6_PROTOTYPE_FAIL SUMMARY step=...`).
- Closed `ISSUE-076` by adding a deterministic bounded-learning proof script (`scripts/check_issue076_learning.sh`), adding a finance regression-fail fixture (`examples/finance/prototype/learning_feedback_regression_fail.json`), verifying observable `show-learned` change after `learn`, verifying reset returns to baseline, and proving regression gate enforcement with deterministic `PERSONALIZATION_LOCAL_REGRESSION_FAILED`.
- Closed `ISSUE-075` by adding runnable replay tooling (`scripts/replay_phase6.py`) with `record` and `verify` commands, generating canonical replay artifact `examples/finance/replay/replay_record.json`, supporting strict and bounded replay verification with deterministic pass/fail codes (`REPLAY_PASS`, mismatch variants), and recording replay evidence payloads (`result_hash`, `policy_hash`, `input_hash`, tolerance bounds).
- Closed `ISSUE-074` by adding deterministic validator conformance script `scripts/check_issue074_validators.sh`, verifying `validate/test/run` for `invoice_completeness_validator_v1.cell`, `vat_math_checker_v1.cell`, and `duplicate_detector_v1.cell`, and asserting exact output matches against canonical expected fixtures under `examples/finance/expected/prototype/`.
- Closed `ISSUE-073` by hardening extractor `cell run` output validation for `cell.finance_doc_extractor_neural_v1`, enforcing required output contract shape plus placeholder-marker rejection with deterministic `BUNDLE_OUTPUT_SCHEMA_INVALID`, and adding an explicit non-placeholder run check command in `docs/ISSUES_PHASE6.md`.
- Closed `ISSUE-072` by adding canonical Phase 6 fixture paths (`examples/finance/prototype`, `examples/finance/replay`, `examples/finance/expected/**`), generating runnable expected outputs from real runner runs, and standardizing Phase 6 demo commands to `--input "$(cat <file.json>)"` in `docs/13_REFERENCE_DEMOS.md` and `docs/ISSUES_PHASE6.md`.
- Closed `ISSUE-071` by redefining Phase 6 as **Prototype Proof (End-to-End)**, adding a mandatory runnability gate in `docs/WORKFLOW.md`, replacing the Phase 6 seed with concrete runnable implementation issues (`ISSUE-072` to `ISSUE-079`), and resetting deterministic next issue selection to `ISSUE-072`.
- Closed `ISSUE-070` by marking Phase 5 CLOSED with summary snapshot `docs/SNAPSHOTS/PHASE5_SUMMARY_2026-03-01.md`, updating phase/index tracking, and recording next issue `ISSUE-071` as the Phase 6 planning seed.
- Closed `ISSUE-069` by publishing consolidated Phase 5 conformance evidence in `docs/SNAPSHOTS/PHASE5_CONFORMANCE_EVIDENCE_2026-03-01.md`, linking pass/fail command outputs across hardening issues (`ISSUE-063` to `ISSUE-068`), and recording deterministic release-gate traceability scope.
- Closed `ISSUE-068` by adding deterministic `--policy-preset <strict|balanced|dev>` support for `validate/test/run`, wiring preset identity into command outputs/conformance keys, implementing deterministic runtime limit profiles for presets, and documenting preset definitions with exact limit behavior in runner and phase docs.
- Closed `ISSUE-067` by documenting the OCI/ORAS distribution compatibility profile, defining transport trust boundaries and runtime equivalence rules in architecture/packaging docs, adding deterministic transport-unpack conformance checks, and correcting the ISSUE-067 test path to the canonical `docs/01_ARCHITECTURE.md`.
- Closed `ISSUE-066` by adding attestation policy modes (`attestation_optional`, `attestation_required`) with `--policy` support in `cell validate`, enforcing deterministic `ATTESTATION_POLICY_VIOLATION` for required-mode missing/invalid attestations, adding fixture/policy files for coverage, and extending `enforcement_report` with attestation policy status.
- Closed `ISSUE-065` by adding SBOM policy modes (`sbom_optional`, `sbom_required`) with `--policy` support in `cell validate`, enforcing deterministic `SBOM_POLICY_VIOLATION` for required-mode failures, adding fixture/policy files for coverage, and extending `enforcement_report` with SBOM policy status.
- Closed `ISSUE-064` by enforcing licensing completeness checks in `cell validate`, adding deterministic `LICENSING_INVALID` failures for missing/incompatible notices/SPDX metadata, adding fixture `fixtures/licensing/missing_notices.cell`, and updating contracts/security docs.
- Closed `ISSUE-063` by enforcing anti-rollback policy in `cell validate` with deterministic `ROLLBACK_REJECTED` for lower versions under strict mode, adding compatibility-mode behavior docs, and adding rollback fixture `fixtures/rollback/older_version.cell`.
- Closed `ISSUE-062` by adding a Phase 5 hardening scope and release gate in `docs/05_PHASE_PLAN.md`, adding a pass/fail release-gate checklist tied to runner commands in `docs/07_TEST_STRATEGY.md`, and recording the dated release-gate decision in `docs/06_DECISIONS.md`.
- Closed `ISSUE-061` by expanding `docs/ISSUES_PHASE5.md` with concrete Phase 5 planning issues (`ISSUE-061` to `ISSUE-070`), marking `ISSUE-061` as `DONE` in `docs/ISSUES_INDEX.md`, and opening deterministic next-issue tracking for `ISSUE-062`.
- Added phase-wise governance tracking with canonical `docs/PHASE_MAP.md`, including deterministic current phase, in-phase remaining count, remaining phase count, and next-issue summary.
- Updated `docs/ISSUES_INDEX.md` to add `MVP_PHASE` per issue row, mark `docs/PHASE_MAP.md` as canonical phase view, and replace the `ISSUE-003` commit placeholder with concrete hash `5e0929c`.
- Updated `docs/PARKING_THREAD_PROMPT.md` to select the next issue by current MVP phase first and only advance when that phase has no remaining `TODO` issues.
- Preserved historical ISSUE numbering and status history without renumbering.

## 2026-02-26

- Initialized repository scaffold and governance docs.
- Added canonical spec file and setup workflow documents.
- Added Phase 0 issue planning index.
- Closed ISSUE-001 by verifying the required repository folder tree and recording snapshot evidence.
- Closed ISSUE-002 by verifying repository hygiene files and `.gitignore` coverage.
- Closed ISSUE-003 by verifying repo-level `AGENTS.md` governance and setup safety rules.
- Closed ISSUE-004 by verifying root pointer files to canonical `/docs` records.

## 2026-02-27

- Closed ISSUE-005 by verifying canonical master spec pointer to docs/SPEC_vFinal.md.
- Closed ISSUE-006 by verifying full vFinal spec content and roadmap readability.
- Closed ISSUE-007 by verifying architecture, security, and contracts starter docs.
- Closed ISSUE-008 by verifying embedding lifecycle and deterministic test strategy docs.
- Closed ISSUE-009 by verifying MVP-0..MVP-5 coverage and MVP-5 CLI references in phase plan.
- Closed ISSUE-010 by verifying decisions log includes dated locked decisions and change control.
- Closed ISSUE-011 by verifying workflow policy sections A-H with naming and hard-stop rules.
- Closed ISSUE-012 by verifying anchor and setup prompt files for deterministic setup behavior.
- Closed ISSUE-013 by verifying parking prompt deterministic next-issue selection rules.
- Closed ISSUE-014 by verifying snapshot and phase summary templates include required sections.
- Closed ISSUE-015 by verifying issues index keys, links, and ISSUE-001..ISSUE-020 tracking rows.
- Closed ISSUE-016 by verifying phase 1 and phase 2 placeholder issue files and format.
- Closed ISSUE-017 by verifying docs README read-first order and docs changelog initial setup entry.
- Closed ISSUE-018 by verifying setup plan includes guard checks, git identity checks, and CI YAML validation.
- Closed ISSUE-019 by verifying GitHub issue template sections and CI placeholder YAML validity.
- Closed ISSUE-020 by re-running setup verification command set and confirming scaffold commit checkpoint.
- Closed ISSUE-021 by creating the Phase 0 close-out summary, seeding concrete Phase 1 issues, updating the index for deterministic next-issue selection, and recording snapshot evidence.
- Closed ISSUE-022 by scaffolding runner CLI entry points for `cell info <bundle>` and `cell validate <bundle>` with deterministic JSON envelopes and stable error codes.
- Closed ISSUE-023 by enforcing safe bundle path handling during `cell validate`, including zip-slip rejection and duplicate normalized path rejection with deterministic error codes.
- Closed ISSUE-024 by rejecting symlink entries during `cell validate` with deterministic `BUNDLE_SYMLINK_NOT_ALLOWED` failures.
- Closed ISSUE-025 by enforcing decompression safety limits in `cell validate` (file count, per-file size, total size, compression ratio) with deterministic `BUNDLE_INVALID`-class errors.
- Closed ISSUE-026 by adding runner-known `manifest.json` parsing/schema validation to `cell validate` with deterministic manifest error codes.
- Closed ISSUE-027 by adding a verifier pack harness for `verifier/tests.json` in `cell validate` with deterministic pass/fail verifier error codes.
- Closed ISSUE-028 by enforcing input schema validation before execution and output schema validation after execution in `cell validate`, with deterministic contract error codes.
- Closed ISSUE-029 by adding hash integrity verification in `cell validate` for canonical `hashes/sha256.json` with compatibility support for `hashes/sha256sums.txt`, including deterministic `HASH_MISMATCH` failures.
- Closed ISSUE-030 by adding conformance gating for `cell run`, requiring a matching verified key (`bundle_hash`, `runner_version`, `policy`) and deterministic re-validation requirements on key mismatch.
- Closed Phase 1 with summary snapshot `docs/SNAPSHOTS/PHASE1_SUMMARY_2026-02-27.md` and recorded next-phase entry requirements.
- Closed ISSUE-031 by replacing Phase 2 placeholders with concrete issues (`ISSUE-031` to `ISSUE-040`), opening Phase 2 status in the index, and recording the planning seed snapshot.
- Closed ISSUE-032 by adding explicit `cell test <bundle>` conformance command support with deterministic pass/fail output, updating runner docs, and recording snapshot evidence.
- Closed ISSUE-033 by adding verifier v0.2 layout compatibility (`verifier/cases.jsonl` with `verifier/expected/`) while keeping v0.1 `verifier/tests.json` support intact and fail-closed for malformed v0.2 cases.
- Closed ISSUE-034 by adding per-case verifier comparison modes (`canonical_json`, `exact_bytes`, `regex`, `numeric_tolerance`), with deterministic unsupported-mode rejection and mode-specific pass/fail validation coverage.
- Closed ISSUE-035 by adding optional integrity extension hooks for signature/provenance metadata refs, enforcing deterministic fail-closed behavior when configured metadata is missing/invalid, while keeping hash verification mandatory and first.
- Closed ISSUE-036 by enforcing WASI offline default-deny policy in `cell run`, exposing offline policy metadata in run output, and rejecting `capabilities.network=true` for WASI bundles with deterministic `OFFLINE_POLICY_VIOLATION`.
- Closed ISSUE-037 by enforcing run-time limits (`max_wall_ms`, `max_output_bytes`, `max_tool_calls`) with deterministic `LIMIT_EXCEEDED` failures and by exposing applied/observed run limits metadata in successful run output.
- Closed ISSUE-038 by enforcing `max_steps` and `max_memory_mb` run policies, including deterministic `LIMIT_EXCEEDED` failures for step/memory overages and explicit `memory_enforcement: best_effort` metadata in successful run output.
- Closed ISSUE-039 by adding a standardized `enforcement_report` to `validate`, `test`, and `run` outputs with tiered offline/filesystem levels and deterministic `limits_applied`/`limits_enforcement` details.
- Closed ISSUE-040 by expanding Phase 2 offline/bounds fixture documentation, adding enforcement command examples, and recording replay evidence across ISSUE-036 to ISSUE-039 checks.

## 2026-02-28

- Closed Phase 2 with summary snapshot `docs/SNAPSHOTS/PHASE2_SUMMARY_2026-02-28.md` and handoff note `docs/SNAPSHOTS/PHASE2_HANDOFF_2026-02-28.md`.
- Updated `docs/05_PHASE_PLAN.md` and `docs/ISSUES_INDEX.md` to record Phase 2 close-out and next-phase entry requirements.
- Opened next planning seed issue `ISSUE-041` in `docs/ISSUES_PHASE3.md` and added Phase 3 tracking in the index as `TODO` (no feature coding started).
- Closed `ISSUE-041` by seeding concrete Phase 3 issues (`ISSUE-041` to `ISSUE-050`), marking Phase 3 active in `docs/ISSUES_INDEX.md`, and recording planning-seed snapshot evidence.
- Closed `ISSUE-042` by aligning MVP-4 demo docs to the then-active legacy dual-demo scope in `docs/13_REFERENCE_DEMOS.md`, confirming consistency with `docs/04_EMBEDDING.md` and `docs/05_PHASE_PLAN.md`, and recording snapshot evidence.
- Closed `ISSUE-043` by switching MVP-4 canonical evidence to Offline Finance & Compliance Desk across embedding, phase plan, reference demos, architecture/testing notes, and governance tracking docs.
- Closed `ISSUE-044` by defining the canonical SDK helper contract and ABI surface in `sdk/README.md`, and linking `docs/04_EMBEDDING.md` plus `runner/README.md` to that single contract reference for deterministic Finance Desk host flows.
- Closed `ISSUE-045` by adding `finance_doc_extractor_neural_v1.cell` with manifest, hashes, schemas, verifier goldens, logic artifact, and representative import fixture, then passing `cell validate`, `cell test`, and `cell run` checks.
- Closed `ISSUE-046` by adding `invoice_completeness_validator_v1.cell` with deterministic required-field/completeness fixtures, representative run input, and passing `cell validate`, `cell test`, and `cell run` checks.
- Closed `ISSUE-047` by adding `vat_math_checker_v1.cell` with deterministic tax-line, rounding, and mismatch fixtures, representative run input, and passing `cell validate`, `cell test`, and `cell run` checks.
- Closed `ISSUE-048` by adding `duplicate_detector_v1.cell` with exact/near-duplicate deterministic ranking fixtures, representative run input, passing `cell validate/test/run`, and confirming trigger flow docs include `on_import`, `on_save`, `on_export`, `on_correct`, and fail-closed behavior.
- Closed `ISSUE-049` by adding Finance Desk gateway allowlist + no-bypass conformance matrix coverage, replay record/result-hash determinism checks, and gateway/replay conformance matrix notes with evidence from selected finance `validate/test/run` checks.
- Closed `ISSUE-050` by marking Phase 3 CLOSED with summary snapshot `docs/SNAPSHOTS/PHASE3_SUMMARY_2026-02-28.md`, updating phase/index tracking, and recording next issue `ISSUE-051` as the Phase 4 planning seed.
- Closed `ISSUE-051` by seeding concrete Phase 4 issues (`ISSUE-051` to `ISSUE-060`), marking Phase 4 active in `docs/ISSUES_INDEX.md`, and recording planning-seed snapshot evidence.
- Closed `ISSUE-052` by documenting deterministic Personal Layer contracts for `personalization.schema.json`, runner-managed storage keyed by `cell.id + cell.version + bundle_hash`, and required `local_regression/` pass/fail gate behavior before apply.
- Closed `ISSUE-053` by adding `cell learn --feedback <json>` CLI scaffold behavior with deterministic success envelope, stable invalid-feedback rejection code (`LEARN_FEEDBACK_INVALID`), and fixture coverage for valid feedback input.
- Closed `ISSUE-054` by enforcing deterministic core identity binding for `cell learn`, rejecting mismatched `cell_id + cell_version + bundle_hash` with stable `PERSONALIZATION_CORE_MISMATCH`, and documenting deterministic `migrate` versus fresh Personal Layer core-change policy.
- Closed `ISSUE-055` by enforcing strict `cell learn` update gating for personalization schema validation, core verifier pass, local regression pass, and bounded size/compute checks before deterministic apply.
- Closed `ISSUE-056` by enforcing Personal Layer bounded growth (daily proposal/compute caps and storage cap), adding deterministic rollback snapshot retention/indexing, and exposing `cell show-learned --detail limits` for limits visibility.
- Closed `ISSUE-057` by adding deterministic transparency reporting for `cell show-learned` and `cell show-learned --json`, including machine-readable metadata and plain-language “what it learned” output with review options.
- Closed `ISSUE-058` by adding `cell reset-personalization` with scoped local reset by `cell_id`, deterministic audit metadata, and safe `--dry-run` preview behavior that does not modify state.
- Closed `ISSUE-059` by adding Finance Desk correction-driven learning and local regression fixtures plus Personal Layer conformance notes in test strategy and observability docs, with deterministic evidence from `cell learn` and `cell test`.
- Closed `ISSUE-060` by marking Phase 4 CLOSED with summary snapshot `docs/SNAPSHOTS/PHASE4_SUMMARY_2026-02-28.md`, updating phase/index tracking, and recording next issue `ISSUE-061` as the Phase 5 planning seed.
