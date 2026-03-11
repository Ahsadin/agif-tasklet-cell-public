# 12 Gateway Profile

Gateway profile for safe external coordination.

## Trust model

- External orchestrator is untrusted.
- Gateway is a strict mediator with allowlist and limits enforcement.
- Runner remains the final enforcement wall for verifier/offline/bounds/learning gates.
- Canonical MVP-4 evidence context is Offline Finance & Compliance Desk.

## Request and response envelopes

All gateway calls must use schema-validated envelopes.

### Request fields

- `request_id`: stable identifier for tracing.
- `cell_id`: requested cell identifier.
- `operation`: requested operation (`validate`, `test`, `run`, `learn`).
- `request_schema_id`: schema identifier for request payload.
- `response_schema_id`: expected response schema identifier.
- `payload_size_bytes`: serialized payload size.
- `rate_token`: caller rate-limit token.
- `policy_hash`: active gateway policy hash.
- `input_json`: canonical input payload when allowed.
- `redacted_input_json`: redacted payload when privacy policy disallows full input.
- `consent_flag`: explicit consent marker for replay/export-sensitive paths.

### Response fields

- `request_id`: echoed request ID.
- `decision`: `allow` or `deny`.
- `decision_reason`: deterministic reason code.
- `applied_policy_hash`: hash of policy actually used.
- `runner_invoked`: boolean.
- `result_ref`: pointer to deterministic result envelope (if allowed).

## Allowlist policy file format

Gateway MUST enforce policy before any Runner call.

Required fields:

- `policy_version`
- `policy_hash`
- `allowed_cells`
- `allowed_ops`
- `limits`

### Example policy (machine-readable)

```json
{
  "policy_version": "1.0.0",
  "policy_hash": "sha256:6d5f5f7a0c2f4fd8f9733f40fdac9e3a06b967f8fcb2c5a8c0d604af6a0438dd",
  "allowed_cells": [
    "finance_doc_extractor_neural_v1.cell",
    "invoice_completeness_validator_v1.cell",
    "vat_math_checker_v1.cell",
    "duplicate_detector_v1.cell"
  ],
  "allowed_ops": {
    "finance_doc_extractor_neural_v1.cell": ["validate", "test", "run"],
    "invoice_completeness_validator_v1.cell": ["validate", "test", "run"],
    "vat_math_checker_v1.cell": ["validate", "test", "run"],
    "duplicate_detector_v1.cell": ["validate", "test", "run"]
  },
  "limits": {
    "max_payload_bytes": 262144,
    "max_requests_per_minute": 60,
    "max_parallel_requests": 4
  }
}
```

### Policy hash computation

- Compute `policy_hash` as SHA-256 over canonical JSON bytes (RFC 8785 / JCS canonicalization).
- Any policy content change requires recomputing `policy_hash`.
- Gateway must reject requests where provided `policy_hash` does not match active policy.

## Transport profile

- Local IPC is default transport (Unix domain socket / named pipe equivalent).
- Remote transport must opt in and preserve the same envelope and enforcement semantics.

## Enforcement order (MUST)

1. Parse request envelope.
2. Validate envelope schema.
3. Validate `policy_hash` against active policy.
4. Enforce allowlist (`allowed_cells`, `allowed_ops`).
5. Enforce size/rate/parallel limits.
6. Only then call Runner.

## Non-bypass invariants

- Gateway cannot invoke execution paths that skip Runner verification.
- Gateway cannot disable Runner offline or resource bounds controls.
- Gateway cannot bypass learning gate checks.
- Gateway cannot elevate capabilities beyond policy allowlist.

## Finance Desk allowlist coverage

Finance Desk gateway policy must remain explicit and minimal:

- Allowlisted Cells only:
  - `finance_doc_extractor_neural_v1.cell`
  - `invoice_completeness_validator_v1.cell`
  - `vat_math_checker_v1.cell`
  - `duplicate_detector_v1.cell`
- Allowlisted operations per cell:
  - `validate`
  - `test`
  - `run`
- Any non-allowlisted `cell_id` or operation must fail closed before Runner invocation.

## Gateway conformance tests

- Malformed envelope is rejected before policy lookup.
- Schema-invalid envelope is rejected with deterministic code.
- Non-allowlisted cell/operation is rejected before Runner call.
- Size limit violations are rejected deterministically.
- Rate limit violations are rejected deterministically.
- No-bypass proofs: test cases confirm gateway cannot trigger Runner paths that skip verifier/offline/bounds/learning gates.

## Finance Desk no-bypass conformance matrix

| Case ID | Gate | Scenario | Expected deterministic result |
|---|---|---|---|
| FD-GW-ALLOW-01 | allowlist | allowlisted Finance Desk cell + allowed op (`run`) | `decision=allow`, `runner_invoked=true`, `decision_reason=ALLOWLIST_OK` |
| FD-GW-DENY-01 | allowlist | non-allowlisted cell id | `decision=deny`, `runner_invoked=false`, `decision_reason=CELL_NOT_ALLOWLISTED` |
| FD-GW-DENY-02 | allowlist | allowlisted cell with disallowed op (`learn`) | `decision=deny`, `runner_invoked=false`, `decision_reason=OP_NOT_ALLOWLISTED` |
| FD-GW-DENY-03 | no-bypass | request tries to skip verifier/conformance state | `decision=deny`, `runner_invoked=false`, `decision_reason=NO_BYPASS_ENFORCED` |
| FD-GW-DENY-04 | no-bypass | request tries to disable offline or limits metadata | `decision=deny`, `runner_invoked=false`, `decision_reason=RUNNER_POLICY_IMMUTABLE` |
| FD-GW-DENY-05 | no-bypass | malformed envelope with forged `policy_hash` | `decision=deny`, `runner_invoked=false`, `decision_reason=POLICY_HASH_MISMATCH` |
