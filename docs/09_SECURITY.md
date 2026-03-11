# 09 Security

## Scope

Phase 5 hardening notes for rollback, licensing, integrity, and deterministic fail-closed behavior.

## Licensing completeness policy (ISSUE-064)

- Runner enforces licensing completeness during `cell validate`.
- Required metadata:
  - `manifest.licensing.notices_path` must point to a bundle-local notices file.
  - SPDX declaration must exist in one accepted field: `spdx_ids`, `spdx_id`, `spdx_identifiers`, or `spdx_identifier`.
- Notices file must exist and be non-empty.
- Missing/incompatible licensing metadata is rejected fail-closed with `LICENSING_INVALID`.

## SBOM attachment policy (ISSUE-065)

- Runner enforces SBOM policy during `cell validate`.
- Supported modes:
  - `sbom_optional` (default): validation may continue when no SBOM is present.
  - `sbom_required`: at least one readable SBOM attachment must be present.
- Policy can be provided using `--policy <json>` with `sbom_policy` mode.
- Missing or unreadable SBOM under `sbom_required` is rejected fail-closed with `SBOM_POLICY_VIOLATION`.
- `enforcement_report` includes SBOM policy mode and observed SBOM status.

## Provenance attestation policy (ISSUE-066)

- Runner enforces provenance attestation policy during `cell validate`.
- Supported modes:
  - `attestation_optional` (default): validation may continue when no attestation is present.
  - `attestation_required`: at least one readable attestation/provenance file must be present.
- Policy can be provided using `--policy <json>` with `attestation_policy` mode.
- Missing or invalid attestations under `attestation_required` are rejected fail-closed with `ATTESTATION_POLICY_VIOLATION`.
- `enforcement_report` includes attestation policy mode and observed attestation status.

## Anti-rollback policy (ISSUE-063)

- Runner enforces anti-rollback during `cell validate`.
- Trust record is local-only and keyed by `manifest.id`.
- Version check is monotonic:
  - numeric dotted versions (for example `1.2.0`) compare numerically,
  - non-numeric versions fall back to lexical compare.

## Modes

- `strict` (default):
  - lower candidate version than trusted version is rejected fail-closed with `ROLLBACK_REJECTED`.
  - accepted candidate updates trusted version/hash.
- `compatibility`:
  - lower candidate version is allowed for compatibility runs.
  - trusted record is not downgraded.

Set mode with environment variable:

- `AGIF_ROLLBACK_MODE=strict`
- `AGIF_ROLLBACK_MODE=compatibility`

## Deterministic error codes

- `LICENSING_INVALID`
- `SBOM_POLICY_VIOLATION`
- `ATTESTATION_POLICY_VIOLATION`
- `ROLLBACK_REJECTED`
- `ROLLBACK_STATE_READ_FAILED`
- `ROLLBACK_STATE_WRITE_FAILED`
- `ROLLBACK_POLICY_INVALID`
- `POLICY_NOT_FOUND`
- `POLICY_INVALID`
