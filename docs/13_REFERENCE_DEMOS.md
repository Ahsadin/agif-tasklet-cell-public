# 13 Reference Demos

Reference demos are mandatory evidence artifacts for MVP-4.

## Canonical MVP-4 hero host app

- Hero host app: Offline Finance & Compliance Desk.
- MVP-4 evidence must come from this host app only.
- Calculator/Email may remain as optional examples, but they are not MVP-4 evidence.

## MVP-4 required demo set

- Demo A (REQUIRED): `finance_doc_extractor_neural_v1.cell`
- Demo B (REQUIRED): `invoice_completeness_validator_v1.cell`
- Demo C (REQUIRED): `vat_math_checker_v1.cell`
- Demo D (REQUIRED): `duplicate_detector_v1.cell`
- Demo E (REQUIRED): Host demo flow trigger scenarios
- Demo F (REQUIRED): Gateway path conformance scenarios
- Demo G (REQUIRED): Replay scenario (record + reproduce)

## Demo A (REQUIRED): finance_doc_extractor_neural_v1.cell

### Task

Routing/classification/extraction/ranking over noisy finance text to structured invoice/receipt fields.
The neural network is quantized and executed inside `logic.wasm`.

### Schema summary

- Input schema: `{ doc_id, source_type, import_event, ocr_text, locale, currency_hint, account_context }`
- Output schema: `{ doc_id, vendor_name, invoice_number, invoice_date, due_date, currency, subtotal, tax_total, grand_total, routing_label, confidence, extracted_fields, warnings }`

### Verifier pack goldens

- Golden count: minimum 120.
- Coverage:
  - low-quality OCR and formatting noise,
  - multilingual headers,
  - missing/ambiguous fields,
  - ranking tie-break and routing consistency,
  - deterministic structured output shape.

### Size budget target

- Target: <= 45 MB total Cell bundle.

### Pass/fail acceptance criteria

- Pass:
  - all goldens pass,
  - output schema is always valid,
  - routing label and extracted field set are stable on repeat runs.
- Fail:
  - any golden mismatch,
  - schema violation,
  - unstable structured output on repeated identical inputs.

### Runner commands

```bash
cell validate cells/finance_doc_extractor_neural_v1.cell
cell test cells/finance_doc_extractor_neural_v1.cell
cell run cells/finance_doc_extractor_neural_v1.cell --input "$(cat examples/finance/prototype/extractor_input.json)"
```

## Demo B (REQUIRED): invoice_completeness_validator_v1.cell

### Task

Deterministic required-field checks, schema validity checks, and completeness warnings for extracted finance records.

### Schema summary

- Input schema: `{ doc_id, extracted_fields, source_type, locale, required_profile }`
- Output schema: `{ doc_id, is_complete, missing_fields, warning_codes, status_code }`

### Verifier pack goldens

- Golden count: minimum 80.
- Coverage:
  - complete invoices,
  - partial receipts,
  - missing vendor/date/totals,
  - schema-invalid extracted payloads,
  - locale-specific required profile differences.

### Size budget target

- Target: <= 8 MB total Cell bundle.

### Pass/fail acceptance criteria

- Pass:
  - all goldens pass,
  - missing field detection is deterministic,
  - warning code set is stable.
- Fail:
  - any golden mismatch,
  - inconsistent required-field decisions,
  - schema-invalid output.

### Runner commands

```bash
cell validate cells/invoice_completeness_validator_v1.cell
cell test cells/invoice_completeness_validator_v1.cell
cell run cells/invoice_completeness_validator_v1.cell --input "$(cat examples/finance/prototype/completeness_input.json)"
```

## Demo C (REQUIRED): vat_math_checker_v1.cell

### Task

Deterministic totals/VAT checks with currency and rounding rules.

### Schema summary

- Input schema: `{ doc_id, currency, tax_lines, subtotal, tax_total, grand_total, rounding_profile }`
- Output schema: `{ doc_id, vat_status, mismatch_flags, computed_totals, rounding_notes, status_code }`

### Verifier pack goldens

- Golden count: minimum 90.
- Coverage:
  - standard VAT rates,
  - mixed tax-line cases,
  - rounding edge cases,
  - currency-specific precision rules,
  - subtotal/tax/grand-total mismatch patterns.

### Size budget target

- Target: <= 8 MB total Cell bundle.

### Pass/fail acceptance criteria

- Pass:
  - all goldens pass,
  - VAT and total checks are deterministic,
  - mismatch flags are stable.
- Fail:
  - any golden mismatch,
  - nondeterministic flag output,
  - schema-invalid output.

### Runner commands

```bash
cell validate cells/vat_math_checker_v1.cell
cell test cells/vat_math_checker_v1.cell
cell run cells/vat_math_checker_v1.cell --input "$(cat examples/finance/prototype/vat_input.json)"
```

## Demo D (REQUIRED): duplicate_detector_v1.cell

### Task

Deterministic duplicate detection using stable heuristics and content hashes.

### Schema summary

- Input schema: `{ doc_id, vendor_name, invoice_number, invoice_date, grand_total, currency, content_hash, candidate_set }`
- Output schema: `{ doc_id, duplicate_detected, duplicate_candidates, match_reason_codes, status_code }`

### Verifier pack goldens

- Golden count: minimum 70.
- Coverage:
  - exact duplicates,
  - near-duplicates by metadata,
  - hash collisions handled fail-closed,
  - non-duplicates with similar totals,
  - deterministic candidate ranking.

### Size budget target

- Target: <= 10 MB total Cell bundle.

### Pass/fail acceptance criteria

- Pass:
  - all goldens pass,
  - duplicate decision is deterministic,
  - candidate ordering is stable.
- Fail:
  - any golden mismatch,
  - unstable duplicate decisions,
  - schema-invalid output.

### Runner commands

```bash
cell validate cells/duplicate_detector_v1.cell
cell test cells/duplicate_detector_v1.cell
cell run cells/duplicate_detector_v1.cell --input "$(cat examples/finance/prototype/duplicate_input.json)"
```

## Demo E (REQUIRED): Host demo flow trigger scenarios

### Task

Validate the host trigger flow in Offline Finance & Compliance Desk:
- `on_import`: extractor -> completeness -> VAT checker,
- `on_save`: completeness -> VAT checker -> duplicate detector,
- `on_export`: produce accounting export JSON interface,
- `on_correct`: emit learning proposal hook payload (hook only, no direct model rewrite).

### Schema summary

- Input schema: `{ trigger_event, doc_context, user_action_context, policy_context }`
- Output schema: `{ trigger_event, executed_cells, decision_trace, accounting_export_json, learning_proposal_hook, fail_closed_actions }`

### Verifier pack goldens

- Golden count: minimum 40.
- Coverage:
  - each trigger path,
  - fail-closed branches,
  - blocked actions under policy,
  - stable decision trace ordering.

### Size budget target

- Target: <= 6 MB fixture/documentation package.

### Pass/fail acceptance criteria

- Pass:
  - all trigger scenarios run through the expected Cell sequence,
  - fail-closed host behavior is deterministic,
  - accounting export interface shape is stable.
- Fail:
  - trigger routes skip required validators,
  - nondeterministic fail-closed behavior,
  - export interface mismatch.

### Runner commands

```bash
cell validate cells/finance_doc_extractor_neural_v1.cell
cell test cells/finance_doc_extractor_neural_v1.cell
cell run cells/finance_doc_extractor_neural_v1.cell --input "$(cat examples/finance/prototype/extractor_input.json)"

cell validate cells/invoice_completeness_validator_v1.cell
cell test cells/invoice_completeness_validator_v1.cell
cell run cells/invoice_completeness_validator_v1.cell --input "$(cat examples/finance/prototype/completeness_input.json)"

cell validate cells/vat_math_checker_v1.cell
cell test cells/vat_math_checker_v1.cell
cell run cells/vat_math_checker_v1.cell --input "$(cat examples/finance/prototype/vat_input.json)"

cell validate cells/duplicate_detector_v1.cell
cell test cells/duplicate_detector_v1.cell
cell run cells/duplicate_detector_v1.cell --input "$(cat examples/finance/prototype/duplicate_input.json)"
```

## Demo F (REQUIRED): Gateway path conformance scenarios

### Task

Demonstrate untrusted orchestrator path with no bypass:
`orchestrator -> gateway -> runner -> allowlisted Cells`.

### Schema summary

- Input schema: `{ request_id, cell_id, operation, policy_hash, payload_size_bytes, input_json }`
- Output schema: `{ request_id, decision, decision_reason, runner_invoked, result_ref, applied_policy_hash }`

### Verifier pack goldens

- Golden count: minimum 30.
- Coverage:
  - allowlisted run path,
  - non-allowlisted cell rejection,
  - non-allowlisted operation rejection,
  - payload/rate limit rejection,
  - deterministic deny reason codes.

### Size budget target

- Target: <= 4 MB policy + fixture package.

### Pass/fail acceptance criteria

- Pass:
  - allowlisted requests reach runner and succeed deterministically,
  - denied requests never invoke runner,
  - deny reason codes are stable.
- Fail:
  - any bypass of allowlist/limits,
  - unstable decision reasoning,
  - missing enforcement metadata.

### Runner commands

```bash
cell validate cells/finance_doc_extractor_neural_v1.cell
cell test cells/finance_doc_extractor_neural_v1.cell
cell run cells/finance_doc_extractor_neural_v1.cell --input "$(cat examples/finance/prototype/extractor_input.json)"

cell validate cells/invoice_completeness_validator_v1.cell
cell test cells/invoice_completeness_validator_v1.cell
cell run cells/invoice_completeness_validator_v1.cell --input "$(cat examples/finance/prototype/completeness_input.json)"
```

## Demo G (REQUIRED): Replay scenario (record + reproduce)

### Task

Demonstrate local-only deterministic replay for finance cases using stored replay records and result hashes.

### Schema summary

- Input schema: `{ replay_id, cell_id, cell_version, bundle_hash, runner_version, policy_hash, input_json, expected_result_hash }`
- Output schema: `{ replay_id, reproduced, result_hash, mismatch_reason, determinism_status }`

### Verifier pack goldens

- Golden count: minimum 20.
- Coverage:
  - successful replay reproduction,
  - replay mismatch detection,
  - redacted-input replay behavior,
  - stable replay hash output.

### Size budget target

- Target: <= 4 MB replay record package.

### Pass/fail acceptance criteria

- Pass:
  - replay reproduces the expected result hash for deterministic cases,
  - mismatch paths return deterministic error state,
  - local-only replay metadata is complete.
- Fail:
  - hash mismatch not surfaced,
  - unstable replay status on repeated runs,
  - missing replay metadata fields.

### Runner commands

```bash
cell validate cells/finance_doc_extractor_neural_v1.cell
cell test cells/finance_doc_extractor_neural_v1.cell
cell run cells/finance_doc_extractor_neural_v1.cell --input "$(cat examples/finance/replay/replay_case_extractor_input.json)" > /tmp/phase6_replay_run.json
python3 scripts/replay_phase6.py record --from /tmp/phase6_replay_run.json --out examples/finance/replay/replay_record.json --mode strict
python3 scripts/replay_phase6.py verify --record examples/finance/replay/replay_record.json --mode strict

cell validate cells/vat_math_checker_v1.cell
cell test cells/vat_math_checker_v1.cell
cell run cells/vat_math_checker_v1.cell --input "$(cat examples/finance/replay/replay_case_vat_input.json)"
```
