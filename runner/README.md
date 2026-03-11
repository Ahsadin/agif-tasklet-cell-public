# Runner CLI Scaffold

This directory contains the `ISSUE-022` CLI scaffold entry point:

- `./runner/cell`

## Commands

- `cell info <bundle>`
- `cell validate <bundle>`
- `cell validate <bundle> --policy <json>`
- `cell validate <bundle> --policy-preset <strict|balanced|dev>`
- `cell validate <bundle> --policy <json> --policy-preset <strict|balanced|dev>`
- `cell test <bundle>`
- `cell test <bundle> --policy-preset <strict|balanced|dev>`
- `cell run <bundle> --input <json>`
- `cell run <bundle> --input <json> --policy-preset <strict|balanced|dev>`
- `cell learn --feedback <json>`
- `cell show-learned`
- `cell show-learned --json`
- `cell reset-personalization --cell-id <cell_id>`
- `cell reset-personalization --cell-id <cell_id> --dry-run`

## Learn scaffold behavior

- `cell learn --feedback <json>` validates `feedback.core_identity` fields:
  - `cell_id`
  - `cell_version`
  - `bundle_hash`
- Optional `feedback.runner_core_identity` may be provided to represent the currently loaded immutable core.
- If proposal core identity does not match runner core identity, command rejects fail-closed with `PERSONALIZATION_CORE_MISMATCH`.
- `feedback.personalization.rules` must be a non-empty array of rule objects (`rule_id`, `rule_text`).
- Gate checks required before apply:
  - `feedback.gate.core_verifier_pass` must be `true`.
  - `feedback.gate.local_regression_pass` must be `true`.
  - bounded size check: `proposed_state_size_bytes <= max_state_size_bytes`.
  - bounded compute check: `proposed_compute_units <= max_compute_units`.
- Bounded growth checks required before apply:
  - daily proposal cap: `max_proposals_per_day`.
  - daily learning compute cap: `max_learning_compute_per_day`.
  - rollback snapshot retention cap: `max_snapshots`.
- Update is applied only when all checks pass; success output includes deterministic `identity_key`.
- `cell show-learned` returns deterministic machine metadata and plain-language "what it learned" lines.
- `cell show-learned --json` returns the same transparency report in explicit JSON format mode.
- Transparency output includes review options text: `Accept / Edit / Reject / Forget`.
- `cell reset-personalization` clears personalization records only for identity keys that match the selected `cell_id`.
- Reset does not touch immutable core bundles and writes deterministic audit metadata in local personalization state.
- `--dry-run` reports exactly what would be cleared without modifying local state.

## SDK helper contract reference

- Canonical SDK helper contract: `sdk/README.md`.
- Runner and SDK helper share one deterministic WASM I/O convention:
  - request JSON enters cell logic through `stdin`,
  - response JSON exits through `stdout`,
  - `stderr` is debug-only and excluded from deterministic output checks.

## Validate safety checks (ISSUE-023)

- Archive entry paths are normalized before trust.
- Any path escaping bundle root is rejected.
- Duplicate normalized paths are rejected.
- Symlink entries are rejected.
- File count is capped at `128` entries.
- Per-file uncompressed size is capped at `1,048,576` bytes.
- Total uncompressed bundle size is capped at `4,194,304` bytes.
- Compression ratio is capped at `100x` per entry.
- `manifest.json` is required and must be valid JSON.
- `manifest.json` must match runner-known required fields and type rules.
- Hash integrity is required before conformance checks.
- Canonical hash manifest: `hashes/sha256.json`.
- Compatibility hash manifest: `hashes/sha256sums.txt`.
- Missing/mismatched hash entries fail closed deterministically.
- Licensing completeness is enforced during `cell validate`:
  - `manifest.licensing.notices_path` must be present and reference an existing non-empty file inside bundle root.
  - SPDX declaration is required (`spdx_ids`, `spdx_id`, `spdx_identifiers`, or `spdx_identifier`) and must be non-empty.
  - missing/incompatible licensing metadata fails with `LICENSING_INVALID`.
- SBOM attachment policy checks are enforced during `cell validate`:
  - supported policy modes: `sbom_optional` (default), `sbom_required`.
  - policy can be loaded from `--policy <json>` (example: `{"sbom_policy":"sbom_required"}`).
  - when `sbom_required` is active, missing/unreadable SBOM attachments fail with `SBOM_POLICY_VIOLATION`.
- Provenance attestation policy checks are enforced during `cell validate`:
  - supported policy modes: `attestation_optional` (default), `attestation_required`.
  - policy can be loaded from `--policy <json>` (example: `{"attestation_policy":"attestation_required"}`).
  - when `attestation_required` is active, missing/invalid attestations fail with `ATTESTATION_POLICY_VIOLATION`.
- Anti-rollback policy is enforced during `cell validate` using a local trust record keyed by `manifest.id`:
  - mode `strict` (default): reject lower `manifest.version` with `ROLLBACK_REJECTED`.
  - mode `compatibility`: allow lower `manifest.version` without replacing the trusted record.
  - set mode with `AGIF_ROLLBACK_MODE=strict|compatibility`.
  - monotonic version comparison uses numeric dotted versions when possible, otherwise lexical fallback.
- Optional integrity extension hooks are supported:
  - Signature metadata refs (for example `manifest.integrity.signature_path`)
  - Provenance metadata refs (for example `manifest.integrity.provenance_path`)
- If integrity extension refs are configured, referenced files must exist and contain valid JSON objects.
- Verifier pack must include one supported layout:
  - `verifier/tests.json` (v0.1 canonical), or
  - `verifier/cases.jsonl` with referenced files under `verifier/expected/` (v0.2 compatibility).
- Input schema is validated before execution for each verifier case.
- Output schema is validated after execution for each verifier case.
- Verifier comparison modes supported per case:
  - `canonical_json`
  - `exact_bytes`
  - `regex`
  - `numeric_tolerance` (requires `float_tolerance`)
- Any failing verifier case fails validation.
- `cell run` is gated by conformance status from `cell validate`.
- Conformance key includes `bundle_hash`, `runner_version`, and `policy`.
- Key mismatch forces re-validation before `run`.
- `cell run` enforces offline default-deny for WASI cells:
  - `execution_kind = wasi` and `capabilities.network = true` is rejected fail-closed.
  - run success output includes `offline_policy` metadata.
- `cell run` enforces runtime limits from `manifest.limits`:
  - `max_wall_ms`
  - `max_steps`
  - `max_memory_mb`
  - `max_output_bytes`
  - `max_tool_calls`
  - limit breaches fail closed with `LIMIT_EXCEEDED`.
  - run success metadata reports `memory_enforcement = best_effort`.
- Deterministic policy presets are supported for `validate`, `test`, and `run`:
  - CLI flag: `--policy-preset <strict|balanced|dev>`.
  - default preset: `balanced`.
  - `strict`: `run` uses manifest limits with hard ceilings:
    - `max_wall_ms <= 500`
    - `max_steps <= 2000`
    - `max_memory_mb <= 64`
    - `max_output_bytes <= 32768`
    - `max_tool_calls <= 3`
  - `balanced`: `run` uses manifest limits as-declared (no preset override).
  - `dev`: `run` uses deterministic minimum floors:
    - `max_wall_ms >= 1500`
    - `max_steps >= 6000`
    - `max_memory_mb >= 128`
    - `max_output_bytes >= 131072`
    - `max_tool_calls >= 8`
  - command output includes `policy_preset`.
- `cell validate`, `cell test`, and `cell run` emit a standardized `enforcement_report`:
  - `offline_level` (`strong`, `best_effort`, `none` tier set)
  - `filesystem_level` and `filesystem_preopens`
  - `limits_applied` and `limits_enforcement`
  - `policy_preset` (applied preset name)
  - `sbom_policy.mode` and `sbom_policy.status` for validate/test policy reporting
  - `attestation_policy.mode` and `attestation_policy.status` for validate/test policy reporting
- `cell test` runs verifier conformance checks directly without requiring `run`.

## Enforcement Examples

```bash
# 1) Offline allow case (WASI with network=false)
./runner/cell run <fixtures_root>/issue036_offline_safe.cell --input '{"value":11}'

# 2) Offline deny case (WASI requesting network)
./runner/cell run <fixtures_root>/issue036_network_requesting.cell --input '{"value":11}'
# Expected: {"ok":false,"error":{"code":"OFFLINE_POLICY_VIOLATION",...}}

# 3) Bounds rejection case
./runner/cell run <fixtures_root>/issue037_timeout_exceed.cell --input '{"value":11,"__simulate_wall_ms":60}'
# Expected: {"ok":false,"error":{"code":"LIMIT_EXCEEDED",...}}

# 4) enforcement_report on validate/test/run
./runner/cell validate <fixtures_root>/issue037_within_limits.cell
./runner/cell test <fixtures_root>/issue037_within_limits.cell
./runner/cell run <fixtures_root>/issue037_within_limits.cell --input '{"value":11}'
```

## Deterministic output contract

- Success:
  - `{"ok":true,"data":{...}}`
- Failure:
  - `{"ok":false,"error":{"code":"...","message":"..."}}`

## Stable error codes

- `USAGE_INVALID`
- `BUNDLE_NOT_FOUND`
- `BUNDLE_NOT_FILE`
- `BUNDLE_ARCHIVE_READ_FAILED`
- `BUNDLE_PATH_ESCAPES_ROOT`
- `BUNDLE_PATH_DUPLICATE`
- `BUNDLE_SYMLINK_NOT_ALLOWED`
- `BUNDLE_TOO_MANY_FILES`
- `BUNDLE_FILE_TOO_LARGE`
- `BUNDLE_TOTAL_SIZE_EXCEEDED`
- `BUNDLE_COMPRESSION_RATIO_EXCEEDED`
- `BUNDLE_MANIFEST_MISSING`
- `BUNDLE_MANIFEST_INVALID_JSON`
- `BUNDLE_MANIFEST_SCHEMA_INVALID`
- `BUNDLE_HASH_MANIFEST_MISSING`
- `BUNDLE_HASH_MANIFEST_INVALID`
- `HASH_MISMATCH`
- `LICENSING_INVALID`
- `SBOM_POLICY_VIOLATION`
- `ATTESTATION_POLICY_VIOLATION`
- `BUNDLE_INTEGRITY_METADATA_MISSING`
- `BUNDLE_INTEGRITY_METADATA_INVALID`
- `ROLLBACK_REJECTED`
- `ROLLBACK_STATE_READ_FAILED`
- `ROLLBACK_STATE_WRITE_FAILED`
- `ROLLBACK_POLICY_INVALID`
- `POLICY_NOT_FOUND`
- `POLICY_INVALID`
- `POLICY_PRESET_INVALID`
- `BUNDLE_VERIFIER_MISSING`
- `BUNDLE_VERIFIER_INVALID`
- `BUNDLE_VERIFIER_FAILED`
- `BUNDLE_SCHEMA_MISSING`
- `BUNDLE_SCHEMA_INVALID`
- `BUNDLE_INPUT_SCHEMA_INVALID`
- `BUNDLE_OUTPUT_SCHEMA_INVALID`
- `CONFORMANCE_REQUIRED`
- `CONFORMANCE_STATE_READ_FAILED`
- `CONFORMANCE_STATE_WRITE_FAILED`
- `OFFLINE_POLICY_VIOLATION`
- `LIMIT_EXCEEDED`
- `INPUT_INVALID_JSON`
- `LEARN_FEEDBACK_INVALID`
- `PERSONALIZATION_CORE_MISMATCH`
- `PERSONALIZATION_CORE_VERIFIER_FAILED`
- `PERSONALIZATION_LOCAL_REGRESSION_FAILED`
- `PERSONALIZATION_LIMIT_EXCEEDED`
- `PERSONALIZATION_DAILY_PROPOSAL_LIMIT_EXCEEDED`
- `PERSONALIZATION_DAILY_COMPUTE_LIMIT_EXCEEDED`
- `PERSONALIZATION_STATE_WRITE_FAILED`
- `PERSONALIZATION_STATE_READ_FAILED`
- `LEARN_EXECUTION_FAILED`
- `SHOW_LEARNED_EXECUTION_FAILED`
- `RESET_PERSONALIZATION_FAILED`
