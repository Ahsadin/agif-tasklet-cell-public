# SDK Helper Contract (Finance Desk MVP-4)

This file is the canonical SDK contract location for MVP-4 host integrations.

## Purpose

The SDK helper gives one deterministic host interface for Finance Desk flows:

- `Cell_Load`
- `Cell_Verify`
- `Cell_Execute`

The host never calls `logic.wasm` directly. The SDK helper routes all calls through Runner policy checks.

## Deterministic result envelope

Every SDK call must return one of these envelopes:

- success: `{"ok":true,"data":{...}}`
- failure: `{"ok":false,"error":{"code":"...","message":"..."}}`

Deterministic error rule:

- no timestamps,
- no random IDs,
- stable `code` values for the same failure class.

## Function contract

### `Cell_Load(bundle_path_json)`

Input JSON:

```json
{
  "bundle_path": "cells/finance_doc_extractor_neural_v1.cell",
  "expected_execution_kind": "wasi"
}
```

Success `data` fields:

- `cell_handle`: opaque stable handle string for this process.
- `bundle_hash`: bundle hash used for conformance keying.
- `runner_version`: runner version string.

Failure examples:

- bundle missing or unreadable,
- unsafe bundle layout,
- integrity/manifest/schema/verifier preconditions not met.

### `Cell_Verify(cell_handle_json)`

Input JSON:

```json
{
  "cell_handle": "handle_001"
}
```

Success `data` fields:

- `valid`: boolean.
- `conformance_key`: `{ bundle_hash, runner_version, policy }`.
- `enforcement_report`: runner enforcement summary.

Failure examples:

- verifier failure,
- hash mismatch,
- schema violation,
- policy mismatch requiring re-validation.

### `Cell_Execute(execute_request_json)`

Input JSON:

```json
{
  "cell_handle": "handle_001",
  "input": {
    "trigger_event": "on_import",
    "doc_id": "doc-123",
    "source_type": "invoice"
  }
}
```

Success `data` fields:

- `output`: schema-valid Cell output.
- `limits`: observed run limits.
- `offline_policy`: applied offline policy metadata.

Failure examples:

- conformance required,
- limit exceeded,
- runtime trap,
- output schema violation.

## ABI boundary (JSON byte contract)

The SDK helper ABI passes UTF-8 JSON bytes only.

- request encoding: UTF-8 JSON object, no BOM.
- response encoding: UTF-8 JSON object, no BOM.
- `request_max_bytes`: `262144` (256 KiB).
- `response_max_bytes`: `1048576` (1 MiB).
- `error_message_max_bytes`: `512`.

ABI failures are deterministic and must not crash the host process.

## Deterministic error mapping

SDK error codes and their runner-aligned meaning:

| SDK code | Meaning |
|---|---|
| `SDK_OK` | Operation succeeded. |
| `SDK_ERR_INVALID_ARGUMENT` | Missing or malformed required input fields. |
| `SDK_ERR_INPUT_TOO_LARGE` | ABI request size exceeded `request_max_bytes`. |
| `SDK_ERR_INVALID_JSON` | Input is not valid UTF-8 JSON object bytes. |
| `SDK_ERR_BUNDLE_INVALID` | Bundle safety/integrity/manifest validation failed. |
| `SDK_ERR_VERIFY_FAILED` | Verifier did not pass; Cell is invalid. |
| `SDK_ERR_CONFORMANCE_REQUIRED` | `Cell_Execute` called without valid conformance state. |
| `SDK_ERR_LIMIT_EXCEEDED` | Runtime limits were exceeded. |
| `SDK_ERR_RUNTIME_TRAP` | Runtime execution trapped. |
| `SDK_ERR_OUTPUT_SCHEMA_VIOLATION` | Execution output failed output schema check. |
| `SDK_ERR_INTERNAL` | Unexpected internal failure, deterministic message required. |

## WASM I/O convention

For WASM cells, the SDK helper follows Runner conventions:

- input JSON bytes are sent via `stdin`,
- output JSON bytes are read from `stdout`,
- `stderr` is debug-only and never part of deterministic output comparison.

## Finance Desk flow rule

For Finance Desk trigger chains, host orchestration must use this order:

1. `Cell_Load`
2. `Cell_Verify`
3. `Cell_Execute`

If any call returns `ok=false`, the host must fail closed and keep normal accounting behavior.
