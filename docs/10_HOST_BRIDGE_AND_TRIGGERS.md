# 10 Host Bridge and Triggers

This document defines the host-bridge contract for Offline Finance & Compliance Desk.

## Purpose

- Map host events to strict Cell input schemas.
- Enforce least privilege between host app and Runner.
- Keep trigger routing deterministic and auditable.

## Least-privilege bridge contract

The host bridge MUST:

- pass only schema-required fields,
- include trigger metadata (`trigger_event`, `doc_id`, `policy_context`),
- avoid ambient authority (no implicit network/file execution powers),
- call Runner APIs for all Cell interactions.

The host bridge MUST NOT:

- bypass verification or conformance gates,
- mutate Cell internals,
- inject undeclared fields into Cell inputs.

## Trigger map

### on_import

- Trigger intent: ingest invoice/receipt/bank export source.
- Runner flow:
  1. `finance_doc_extractor_neural_v1.cell`
  2. `invoice_completeness_validator_v1.cell`
  3. `vat_math_checker_v1.cell`
- Required input mapping:
  - document text/context -> extractor input schema,
  - extractor output -> validator/checker schemas.

### on_save

- Trigger intent: enforce deterministic validation before persisting a record.
- Runner flow:
  1. `invoice_completeness_validator_v1.cell`
  2. `vat_math_checker_v1.cell`
  3. `duplicate_detector_v1.cell`
- Required input mapping:
  - normalized record payload,
  - candidate duplicate context,
  - policy context.

### on_export

- Trigger intent: produce stable accounting export interface.
- Runner flow:
  - validators and duplicate checks must already be clean,
  - output envelope must include deterministic `accounting_export_json` structure.
- Required input mapping:
  - validated finance record set + export profile.

### on_correct

- Trigger intent: capture user correction and propose local learning update.
- Runner flow:
  - create learning proposal hook payload only,
  - proposal is evaluated later by MVP-5 learning gate.
- Required input mapping:
  - correction details,
  - prior extraction context,
  - user approval metadata.

## Fail-closed trigger behavior

- If any required cell fails verification: trigger result is denied and feature path is disabled.
- If execution returns schema/limit/offline/integrity error: host ignores output and keeps safe default UX.
- If duplicate or VAT checks fail on save/export path: host blocks persistence/export until user resolves issues.

## Deterministic host evidence requirements

For each trigger path, evidence must show:

- exact input envelope shape,
- exact sequence of invoked cells,
- deterministic pass/fail outcome,
- stable error code when fail-closed.
