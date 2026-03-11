# 01 Architecture

## Modules

- `runner/`: runtime that loads, verifies, and executes Cells.
- `sdk/`: helper layer for deterministic WASM I/O conventions.
- `cells/`: single-task Cells.
- `tools/`: packaging and canonical JSON utilities.
- `examples/`: host embedding examples.

## Lifecycle + Boundaries

- Host app calls Runner APIs only (`load -> verify -> execute`).
- Host app provides minimal schema-required context only.
- Runner enforces offline policy, integrity checks, schema checks, and limits.
- Cell bundle provides task logic, schemas, verifier pack, and integrity metadata.

## Distribution trust boundary (OCI/ORAS transport)

- OCI/ORAS is a distribution transport layer, not a runtime trust authority.
- Runner trust is derived from local bundle verification (`manifest.json`, hash integrity, policy checks), not registry-side metadata.
- OCI tags, annotations, and repository naming are treated as informational transport metadata.
- Runtime behavior must be equivalent after transport:
  - validate/test/run on a pulled bundle must match the same checks as a locally packaged bundle.
- If transport metadata conflicts with bundle-local metadata, runner behavior follows the bundle-local metadata.

## Hero host reference

Offline Finance & Compliance Desk is the canonical MVP-4 host evidence context.

Reference Cell set:

- `finance_doc_extractor_neural_v1.cell`
- `invoice_completeness_validator_v1.cell`
- `vat_math_checker_v1.cell`
- `duplicate_detector_v1.cell`

## Data flow

1. Host receives trigger event and builds minimal schema input.
2. Runner loads bundle and validates manifest/integrity.
3. Runner validates schemas and verifier pack status.
4. Runner executes allowed Cell path.
5. Host applies output on success, or fails closed on error.
