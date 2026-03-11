# 08 Training and Packaging

This document defines the offline training-to-bundle lifecycle for the Finance Desk neural reference cell.

## Scope

- Applies to `finance_doc_extractor_neural_v1.cell`.
- Keeps deterministic runner contracts intact.

## Lifecycle

1. Curate finance extraction dataset and edge-case set.
2. Train/update model profile for routing/classification/extraction/ranking.
3. Export fixed inference artifact and quantize for compact local execution.
4. Generate verifier goldens from curated evaluation cases.
5. Package `.cell` bundle with manifest, schemas, verifier pack, logic, and hashes.
6. Validate/test in runner before release.

## Training artifacts

- Dataset schema and version metadata.
- Training config and seed metadata.
- Exported quantized model weights and metadata.
- Golden test generation report.

## Packaging requirements

- Bundle includes deterministic schema contracts.
- Bundle includes verifier pack with required coverage.
- Bundle includes integrity manifest.
- Bundle size stays within documented budget.

## OCI/ORAS distribution compatibility profile (ISSUE-067)

This profile allows `.cell` bundles to be distributed through OCI registries (via ORAS) without changing runner trust semantics.

### Transport mapping

- Artifact payload MUST be the original `.cell` file bytes.
- Recommended artifact media type:
  - `application/vnd.agif.cell.bundle.v1+zip`
- Tags and OCI annotations are transport metadata only and are not part of runtime trust.
- Pull results must write a local `.cell` file before runner execution.

### Offline verify and hash rules

- Runtime execution remains offline-first:
  - network is only for distribution transport (`oras push`/`oras pull`), not for `cell validate/test/run`.
- The pulled `.cell` file must be verified locally using existing integrity rules:
  - `./runner/cell validate <pulled_bundle.cell>`
- Transport equivalence requirement:
  - source `.cell` and pulled `.cell` must be byte-equivalent (`sha256` and `cmp` match).
- If hashes differ after transport/unpack, treat artifact as non-equivalent and fail release promotion.

### Deterministic compatibility scope

- Compatible transport path:
  - local `.cell` -> OCI/ORAS transport -> local `.cell` -> runner validate/test/run.
- Out of scope for runner trust:
  - registry availability, tag mutability, and non-bundle transport metadata.

## MVP-5 Personalization packaging boundary

- Personal Layer files are not packaged inside the signed `.cell` archive.
- Runner-managed layout must be keyed by `cell.id + cell.version + bundle_hash`, for example:

```text
personalization/<cell.id>/<cell.version>/<bundle_hash>/
  personalization.schema.json
  personalization_state.json
  local_regression/
    tests.json
```

- `personalization.schema.json` defines allowed personalization records and must be validated before any apply decision.
- `local_regression/` defines required local replay checks that must pass before personalization apply is allowed.
- Missing schema or failing local regression is a deterministic fail-closed gate result.

## Determinism requirements

- Fixed training/export metadata captured for auditability.
- Deterministic post-processing rules documented.
- Tolerance policy declared where bounded numeric drift is expected.

## MVP evidence link

- Demo requirements and command evidence: `docs/13_REFERENCE_DEMOS.md`.
- Neural profile details: `docs/09_NEURAL_CELL_PROFILE.md`.
