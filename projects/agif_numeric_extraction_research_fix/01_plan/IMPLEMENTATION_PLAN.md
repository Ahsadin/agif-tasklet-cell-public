# Implementation Plan

## Stage 1
- Replace placeholder numeric extraction inside `intelligence/wasm/src/lib.rs`.
- Remove the v6 runner post-processing patch from `runner/cell`.

## Stage 2
- Strengthen A6 cases and gate logic.
- Add Rust tests for invoice-number rejection, tax extraction, subtotal consistency, and abstention.

## Stage 3
- Add deterministic public/private data manifests and training/export scaffolding.
- Record public source metadata and private-holdout summaries under this initiative.

## Stage 4
- Rebuild the v6 bundle, rerun verification, and update paper support text.
