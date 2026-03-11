# 04 Embedding

## Hero host app

Offline Finance & Compliance Desk is the canonical MVP-4 host demo.

## Host integration lifecycle

1. `Cell_Load(bundle_path)`
2. `Cell_Verify(cell_instance)`
3. `Cell_Execute(cell_instance, input_json)`

The host app always calls the Runner for verification and execution. Cells are never invoked directly from host UI code.

## Canonical SDK helper contract

- Canonical contract location: `sdk/README.md`.
- This contract defines `Cell_Load`, `Cell_Verify`, and `Cell_Execute` inputs/outputs, ABI JSON byte limits, and deterministic error mapping.
- Host integrations must follow the same SDK helper and WASM I/O conventions (`stdin`/`stdout`) documented there.

## Fail-closed UX rules

- If `Cell_Verify` fails: disable the feature for that document and show a deterministic "verification failed" state.
- If `Cell_Execute` returns schema/limit/integrity/offline errors: ignore cell output and keep normal host behavior.
- If any required cell in a trigger chain fails: stop the chain and return deterministic warning state.
- Never auto-commit accounting data when any validation cell fails.

## Least-privilege host bridge

The host bridge passes only minimal schema-required context:

- Document content context required for extraction/validation.
- Event context (`on_import`, `on_save`, `on_export`, `on_correct`).
- Policy context required for allowlist and deterministic enforcement metadata.

The bridge does not grant ambient capabilities (no implicit filesystem/network execution rights).

## Trigger mapping to input schema

### on_import

- Trigger payload maps to extractor input schema (`doc_id`, `source_type`, `ocr_text`, `locale`, `currency_hint`, `account_context`).
- Host flow: `finance_doc_extractor_neural_v1.cell` -> `invoice_completeness_validator_v1.cell` -> `vat_math_checker_v1.cell`.

### on_save

- Trigger payload maps to validation schema inputs plus candidate history.
- Host flow: `invoice_completeness_validator_v1.cell` -> `vat_math_checker_v1.cell` -> `duplicate_detector_v1.cell`.

### on_export

- Trigger payload includes validated finance record set and export profile.
- Host output interface: deterministic `accounting_export_json` envelope (export implementation can be extended later; interface must remain stable now).

### on_correct

- Trigger payload includes user correction details and prior extraction context.
- Host emits a learning proposal hook payload only (MVP-5 gate decides whether proposal is accepted).

## MVP-4 evidence requirement

MVP-4 evidence is the Finance Desk flow only:
- one neural extraction cell,
- three deterministic validation/compliance cells,
- host trigger mappings,
- fail-closed outcomes on every trigger path.

Reference evidence details are defined in `docs/13_REFERENCE_DEMOS.md`.
Bridge rules are defined in `docs/10_HOST_BRIDGE_AND_TRIGGERS.md`.
Gateway controls are defined in `docs/12_GATEWAY_PROFILE.md`.
Replay rules are defined in `docs/11_OBSERVABILITY_AND_REPLAY.md`.
