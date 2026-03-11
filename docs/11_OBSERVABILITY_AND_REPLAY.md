# 11 Observability and Replay

This document defines local-only observability and deterministic replay requirements for Offline Finance & Compliance Desk.

## Local-only observability policy

- All logs remain local.
- Default logging is redacted for sensitive finance fields.
- Retention is bounded and user-controlled.
- No cloud telemetry is required for MVP evidence.

## Deterministic event log record

Each record should capture:

- `record_id`
- `timestamp_local`
- `trigger_event`
- `cell_id`
- `cell_version`
- `bundle_hash`
- `runner_version`
- `policy_hash`
- `result_code`
- `result_hash`
- `enforcement_report`

## Replay record contract

A replay record must be sufficient to reproduce a prior case offline:

- `replay_id`
- `cell_id`
- `cell_version`
- `bundle_hash`
- `runner_version`
- `policy_hash`
- `input_json`
- `expected_result_hash`

### Replay record schema notes (deterministic)

- `expected_result_hash` and produced `result_hash` MUST use the same deterministic algorithm:
  - canonical JSON serialization of the full result envelope,
  - SHA-256 over canonical bytes,
  - stored as `sha256:<hex>`.
- Replay records SHOULD also store:
  - `request_hash` (`sha256:<hex>` of canonical input envelope),
  - `gateway_decision` (`allow`/`deny`),
  - `gateway_decision_reason`,
  - `runner_invoked` boolean.
- Any missing required replay fields is a deterministic replay-contract failure.

## Replay procedure

1. Validate bundle integrity and conformance status.
2. Re-run the same cell with replay input.
3. Compare reproduced result hash to expected hash.
4. Emit deterministic replay status (`reproduced` or `mismatch`).

## Deterministic result_hash checks

- `result_hash` MUST be stable across repeated runs for identical:
  - `bundle_hash`,
  - `runner_version`,
  - `policy_hash`,
  - `input_json`.
- If `result_hash` differs, replay status MUST be `mismatch` with deterministic reason code.
- Expected mismatch reason codes:
  - `REPLAY_RESULT_HASH_MISMATCH`
  - `REPLAY_POLICY_HASH_MISMATCH`
  - `REPLAY_BUNDLE_HASH_MISMATCH`
  - `REPLAY_INPUT_HASH_MISMATCH`

## Replay acceptance criteria

- Finance extraction case can be reproduced with same result hash.
- VAT math case can be reproduced with same result hash.
- Duplicate detection case can be reproduced with same result hash.
- Mismatch case returns deterministic mismatch reason.

## Personal Layer learning observability (MVP-5)

- Finance Desk replay logs must include Personal Layer learning events with:
  - `learning_feedback_id`,
  - `core_identity_key` (`cell.id + cell.version + bundle_hash`),
  - `local_regression_status` (`pass`/`fail`),
  - `learn_apply_status` (`applied`/`rejected`) and deterministic reason code when rejected.
- Correction-driven Finance Desk learning evidence should reference `examples/finance/learning_feedback.json`.
- Local regression evidence should reference `examples/finance/local_regression_after_learning_input.json` and the corresponding `cell test` conformance result.
- Personal Layer replay checks must prove learning updates do not bypass core Finance Desk verifier guarantees.

## Finance Desk replay matrix

| Case ID | Cell | Replay expectation | Deterministic check |
|---|---|---|---|
| FD-RP-01 | `finance_doc_extractor_neural_v1.cell` | reproduce prior on-import result | produced `result_hash` equals `expected_result_hash` |
| FD-RP-02 | `vat_math_checker_v1.cell` | reproduce VAT calculation result | produced `result_hash` equals `expected_result_hash` |
| FD-RP-03 | `duplicate_detector_v1.cell` | reproduce duplicate ranking result | produced `result_hash` equals `expected_result_hash` |
| FD-RP-04 | any Finance Desk cell | policy changed | deterministic mismatch with `REPLAY_POLICY_HASH_MISMATCH` |
| FD-RP-05 | any Finance Desk cell | input changed | deterministic mismatch with `REPLAY_INPUT_HASH_MISMATCH` |

## Gateway and replay interaction

- Gateway metadata (`policy_hash`, `decision`) must be present in replay records for gateway-routed requests.
- Replay must prove no-bypass path was preserved (`gateway -> runner -> cell`).

## Evidence requirements for MVP-4

- At least one replay record for each trigger family (`on_import`, `on_save`, `on_export`).
- At least one deterministic mismatch replay case.
- Snapshot evidence must include commands, outputs, and resulting hashes.
