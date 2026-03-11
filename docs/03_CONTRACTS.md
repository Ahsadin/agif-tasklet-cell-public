# 03 Contracts

## Core contracts

- Input schema: `schemas/input.schema.json`
- Output schema: `schemas/output.schema.json`
- Verifier pack (v0.1): `verifier/tests.json`

## MVP-5 Personal Layer contracts

- Personal Layer state is stored outside the signed `.cell` bundle under a runner-managed path keyed by `cell.id + cell.version + bundle_hash`.
- `personalization.schema.json` is required and defines the accepted feedback/proposal payload for local learning updates.
- `local_regression/` is required for proposal gating and must contain deterministic regression cases tied to the same core identity key.
- Learn payload core identity binding uses `cell.id + cell.version + bundle_hash`; mismatch against runner core identity is rejected fail-closed.
- Validation is fail-closed: if `personalization.schema.json` is missing/invalid, the proposal must be rejected.
- Regression gating is fail-closed and deterministic: if any `local_regression/` case fails, personalization apply is rejected.

## Comparison modes

- `canonical_json` (default)
- `exact_bytes`
- `regex`
- `numeric_tolerance`

## Compatibility notes

- Hash manifests accepted: `hashes/sha256.json` (canonical), `hashes/sha256sums.txt` (compat).
- Verifier pack compatibility: canonical v0.1 and accepted alternate layouts.

## Licensing contract

- `manifest.licensing.notices_path` is required and must reference a bundle-local notices file.
- SPDX declaration is required via one accepted key:
  - `manifest.licensing.spdx_ids`
  - `manifest.licensing.spdx_id`
  - `manifest.licensing.spdx_identifiers`
  - `manifest.licensing.spdx_identifier`
- Runner validation fails closed with `LICENSING_INVALID` when licensing metadata is missing or incompatible.

## SBOM policy contract

- Validation policy supports:
  - `sbom_optional` (default)
  - `sbom_required`
- When `sbom_required` is active, bundle must include at least one readable SBOM attachment.
- Missing/unreadable SBOM under required mode fails closed with `SBOM_POLICY_VIOLATION`.

## Attestation policy contract

- Validation policy supports:
  - `attestation_optional` (default)
  - `attestation_required`
- When `attestation_required` is active, bundle must include at least one readable attestation/provenance attachment.
- Missing/invalid attestation under required mode fails closed with `ATTESTATION_POLICY_VIOLATION`.

## Versioning

- v0.1 and v0.2 compatibility must be explicit in runner validation output.
