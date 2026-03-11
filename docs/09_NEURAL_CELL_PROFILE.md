# 09 Neural Cell Profile

Profile baseline for the Finance Desk neural reference Cell.

## Cell identity

- Bundle name: `finance_doc_extractor_neural_v1.cell`
- Role: routing/classification/extraction/ranking over noisy finance text.

## Inference boundary

- Inference runs locally inside `logic.wasm`.
- Output is always schema-validated by Runner.

## Required profile fields

- Model type and quantization metadata.
- Determinism mode and seed policy.
- Supported output labels/routing classes.
- Confidence scoring policy.
- Post-processing rules for deterministic structured output.

## Output behavior constraints

- Output must remain inside declared schema.
- Ranking order and tie-break policy must be deterministic.
- Warnings must use stable warning code set.

## Golden coverage expectations

- OCR noise and partial text.
- Missing/ambiguous numeric fields.
- Multi-currency and locale variation.
- Edge-case routing labels.

## Compatibility requirements

- Works with verifier v0.1 and v0.2 layouts supported by Runner.
- Honors offline and bounded execution policies.

## MVP evidence links

- Training and packaging lifecycle: `docs/08_TRAINING_AND_PACKAGING.md`.
- Hero demo requirements: `docs/13_REFERENCE_DEMOS.md`.
