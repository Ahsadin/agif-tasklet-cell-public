# 05 Phase Plan

This plan must stay aligned with `docs/SPEC_vFinal.md`.

## Governance gates

- One issue per thread.
- No product code during setup phase issues.
- If `SPEC_NOT_PASTED_YET_DO_NOT_START` appears in `docs/SPEC_vFinal.md`, implementation must stop.
- Paper reference artifact is required in `docs/PAPER_OUTLINE.md`.

## MVP-0 Runner skeleton

### Scope

- CLI skeleton for `cell info` and `cell validate`.
- Bundle opening safety checks.
- Deterministic error JSON shape.

### Acceptance criteria (testable)

- Zip-slip defense check defined and passing.
- Symlink ban check defined and passing.
- Decompression limits defined (total/per-file/file-count/compression-ratio) and tested at planning level.
- Deterministic error contract documented with fixed codes.

### Tests

- Documentation test cases for safe vs unsafe archive scenarios.
- Checklist confirms all four safety controls are present.

## MVP-1 Contracts + verifier harness

### Scope

- Schema validation flow.
- Verifier pack run path.
- Conformance gating behavior.

### Acceptance criteria (testable)

- Input validated before execution.
- Output validated after execution.
- Failed verifier marks Cell invalid.

### Tests

- Golden case pass/fail documentation matrix.

## MVP-2 Integrity

### Scope

- Mandatory SHA-256 verification.
- Optional signature hook points.
- v0.1/v0.2 compatibility notes.

### Acceptance criteria (testable)

- Hash mismatch produces deterministic fail-closed result.
- Compatibility behavior documented for accepted hash manifest variants.

### Tests

- Hash pass/fail scenario checklist.

## MVP-3 Offline + bounds

### Scope

- WASI default deny stance.
- Fuel/timeouts/output caps policy.
- Enforcement report format.

### Acceptance criteria (testable)

- Offline/network denial is default policy.
- Limits documented: wall time, steps, memory, output bytes, tool calls.
- Per-run enforcement report schema exists in docs.

### Tests

- Bounded-execution checklist and expected rejection scenarios.

## MVP-4 Native embedding demos + SDK

### Scope

- Hero host app: Offline Finance & Compliance Desk.
- Host embedding lifecycle docs and trigger mapping.
- One neural cell + three deterministic validation/compliance cells as canonical evidence.
- SDK helper boundaries for deterministic WASM I/O.

### Acceptance criteria (testable)

- Finance Desk host demo flows exist and are testable (`on_import`, `on_save`, `on_export`, `on_correct`).
- One neural Cell (`finance_doc_extractor_neural_v1.cell`) and three deterministic Cells (`invoice_completeness_validator_v1.cell`, `vat_math_checker_v1.cell`, `duplicate_detector_v1.cell`) are integrated as MVP-4 evidence.
- Demo requirements are defined in `docs/13_REFERENCE_DEMOS.md` (schema summary, goldens, size budget, pass/fail criteria, runner commands).
- Host bridge rules are referenced from `docs/10_HOST_BRIDGE_AND_TRIGGERS.md`.
- Gateway rules are referenced from `docs/12_GATEWAY_PROFILE.md`.
- Replay rules are referenced from `docs/11_OBSERVABILITY_AND_REPLAY.md`.
- Conformance tests are referenced from `docs/07_TEST_STRATEGY.md`.

### Tests

- Host trigger integration checklist for `on_import`, `on_save`, `on_export`, and `on_correct`.
- Gateway no-bypass conformance checks from `docs/12_GATEWAY_PROFILE.md`.
- Replay reproducibility checks from `docs/11_OBSERVABILITY_AND_REPLAY.md`.
- Conformance matrix checks from `docs/07_TEST_STRATEGY.md`.

## MVP-5 Local-only Personal Learning Layer

### Scope

- Personalization store and schema.
- Proposal gate + local regression policy.
- User transparency notes ("what I learned").

### Required CLI references

- `cell learn --feedback <json>`
- `cell show-learned`
- `cell reset-personalization`

### Acceptance criteria (testable)

- Personalization is keyed to core identity (`cell.id + cell.version + bundle_hash`).
- `personalization.schema.json` requirements are documented with fail-closed validation behavior.
- `local_regression/` harness requirements are documented with pass-all-before-apply behavior.
- Mismatched core identity is rejected deterministically before apply.
- On core change, policy is deterministic: explicit `migrate` path with tests or start a fresh Personal Layer.
- Update gate requires core verifier pass + local regression pass.
- All three MVP-5 commands are listed in docs and issue planning.

### Tests

- Documentation checklist for gate pass/fail and rollback behavior.

## Phase 5 post-MVP-5 hardening track

### Scope boundaries

- In scope:
  - anti-rollback policy enforcement planning (`ISSUE-063`)
  - licensing completeness validation planning (`ISSUE-064`)
  - SBOM and attestation policy checks planning (`ISSUE-065`, `ISSUE-066`)
  - OCI/ORAS compatibility profile documentation (`ISSUE-067`)
  - deterministic policy preset documentation/implementation planning (`ISSUE-068`, presets: `strict`, `balanced`, `dev`, flag: `--policy-preset`)
  - conformance evidence and phase close-out documentation (`ISSUE-069`, `ISSUE-070`)
- Out of scope:
  - new host demo features
  - canonical behavior changes in `docs/SPEC_vFinal.md`
  - cloud-connected runtime requirements

### Release gate for Phase 5 close-out

- Gate condition 1: `ISSUE-063` to `ISSUE-069` are completed and indexed as `DONE`.
- Gate condition 2: required conformance checks in `docs/07_TEST_STRATEGY.md` show pass/fail outcomes with deterministic expectations.
- Gate condition 3: phase summary evidence exists before close-out (`docs/SNAPSHOTS/PHASE5_SUMMARY_YYYY-MM-DD.md`).
- Gate condition 4: release gate decision remains recorded in `docs/06_DECISIONS.md` with date, reason, and impacted files.

## Phase 6 Prototype Proof (End-to-End)

### Scope boundaries

- In scope:
  - runnable Offline Finance & Compliance Desk prototype evidence across `validate/test/run/replay/learning`
  - concrete example inputs/outputs and deterministic fixture coverage for reference cells
  - one-command runbook proof for end-to-end demo execution
- Out of scope:
  - phase close-out with docs-only evidence
  - non-runnable conceptual acceptance notes
  - canonical behavior edits in `docs/SPEC_vFinal.md`

### Prototype Proof Gate (mandatory)

- Phase 6 cannot be marked `CLOSED` unless a one-command runbook demonstrates all of:
  - `validate`
  - `test`
  - `run`
  - replay reproduction
  - learning demo (`learn -> show-learned -> reset`)
- Required evidence snapshot for close-out:
  - `docs/SNAPSHOTS/PHASE6_PROTOTYPE_EVIDENCE_YYYY-MM-DD.md`
- Evidence must include:
  - exact command lines executed locally
  - captured stdout/stderr
  - concrete artifact paths proving outputs were produced in-repo

## Threading strategy

- Setup thread runs once for scaffold + docs + first commit.
- PARKING thread stays persistent and recommends one next issue.
- Every implementation thread after setup must target a single `ISSUE-XXX`.

## Phase close-out log

- 2026-02-27: Phase 1 is closed.
- Summary snapshot: `docs/SNAPSHOTS/PHASE1_SUMMARY_2026-02-27.md`.
- Next entry requirement: seed concrete Phase 2 issues in `docs/ISSUES_PHASE2.md` before selecting the next implementation issue.
- 2026-02-28: Phase 2 is closed.
- Summary snapshot: `docs/SNAPSHOTS/PHASE2_SUMMARY_2026-02-28.md`.
- Handoff note: `docs/SNAPSHOTS/PHASE2_HANDOFF_2026-02-28.md`.
- Next entry requirement: start `ISSUE-041` (Phase 3 planning seed) in `docs/ISSUES_PHASE3.md` before selecting the next feature implementation issue.
- 2026-02-28: Phase 3 is CLOSED.
- Summary snapshot: `docs/SNAPSHOTS/PHASE3_SUMMARY_2026-02-28.md`.
- Next issue: `ISSUE-051` (Phase 4 planning seed) in `docs/ISSUES_PHASE4.md`.
- Next entry requirement: complete `ISSUE-051` before selecting the next feature implementation issue.
- 2026-02-28: Phase 4 is CLOSED.
- Summary snapshot: `docs/SNAPSHOTS/PHASE4_SUMMARY_2026-02-28.md`.
- Next issue: `ISSUE-061` (Phase 5 planning seed) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-061` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 hardening scope and release gate were defined.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-062.md`.
- Next issue: `ISSUE-063` (Phase 5 anti-rollback policy) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-063` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 anti-rollback policy was implemented.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-063.md`.
- Next issue: `ISSUE-064` (Phase 5 licensing completeness checks) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-064` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 licensing completeness checks were implemented.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-064.md`.
- Next issue: `ISSUE-065` (Phase 5 SBOM policy checks) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-065` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 SBOM policy checks were implemented.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-065.md`.
- Next issue: `ISSUE-066` (Phase 5 provenance attestation policy checks) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-066` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 provenance attestation policy checks were implemented.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-066.md`.
- Next issue: `ISSUE-067` (Phase 5 OCI/ORAS compatibility profile) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-067` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 OCI/ORAS compatibility profile docs were implemented.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-067.md`.
- Next issue: `ISSUE-068` (Phase 5 deterministic policy preset profiles) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-068` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 deterministic policy preset profiles were implemented (`--policy-preset strict|balanced|dev`).
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-068.md`.
- Next issue: `ISSUE-069` (Phase 5 conformance evidence bundle) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-069` before selecting the next feature implementation issue.
- 2026-03-01: Phase 5 conformance evidence bundle was consolidated.
- Snapshot: `docs/SNAPSHOTS/PHASE5_CONFORMANCE_EVIDENCE_2026-03-01.md`.
- Next issue: `ISSUE-070` (Phase 5 close-out and handoff) in `docs/ISSUES_PHASE5.md`.
- Next entry requirement: complete `ISSUE-070` before phase close-out.
- 2026-03-01: Phase 5 is CLOSED.
- Summary snapshot: `docs/SNAPSHOTS/PHASE5_SUMMARY_2026-03-01.md`.
- Next issue: `ISSUE-071` (Phase 6 planning seed) in `docs/ISSUES_PHASE6.md`.
- Next entry requirement: complete `ISSUE-071` before selecting the next feature implementation issue.
- 2026-03-01: Phase 6 was redefined as Prototype Proof (End-to-End) with a mandatory runnability gate.
- Snapshot: `docs/SNAPSHOTS/SNAPSHOT_2026-03-01_ISSUE-071_BACK_ON_TRACK.md`.
- Next issue: `ISSUE-072` (Phase 6 finance example fixtures and expected outputs) in `docs/ISSUES_PHASE6.md`.
- Next entry requirement: complete `ISSUE-072` before selecting the next feature implementation issue.
- 2026-03-01: Prototype Proof Gate passed for Phase 6 with runnable end-to-end evidence.
- Prototype evidence snapshot: `docs/SNAPSHOTS/PHASE6_PROTOTYPE_EVIDENCE_2026-03-01.md`.
- 2026-03-01: Phase 6 is CLOSED.
- Summary snapshot: `docs/SNAPSHOTS/PHASE6_SUMMARY_2026-03-01.md`.
- Next issue: none (all currently planned MVP issues are complete).
