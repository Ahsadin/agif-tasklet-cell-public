# AGIF Tasklet Cell

## Unified Final Spec (vFinal)

**Date:** 2026-02-26
**Status:** Consolidated concept + implementable spec + Codex build plan + local-only learning extension

## Source set integrated

This document merges and reconciles the following project reports (preserving key claims and language where possible):

* **01. AGIF Offline Agent Artifact.docx**
* **02. AGIF Security Report v0.2.docx**
* **03. Gemini Offline Agent Module Plan.docx**
* **04. Sealed Offline Agent Module Report.docx**
* **AGIF Desktop Security Report.md**

Conceptual ancestry / alignment references:

* **Adaptive General Intelligence Fabric (AGIF) A Publish‑Ready Concept Paper.docx**
* **ENF-Whitepaper-v1.0.1-2025-10-09.pdf**

---

## 1) Concept

You are defining a new class of software artifact: a **Sealed Offline Single‑Task Agent Module** (also called a **Cell / Tasklet / Module**).

A Tasklet Cell is:

* **Embedded natively** inside a host application (e.g., Calculator, Email client, POS, accounting tool).
* **Offline-first and enforceably offline** (the runner denies network by default).
* **Single-task** (one module = one bounded job).
* **Deterministic or strictly bounded** (declared limits + declared determinism mode).
* **Contract-driven** (strict input/output schemas).
* **Self-verifying** (ships with a **Verifier Pack** of golden tests; passing is mandatory for validity).
* **Firmware-like integrity** (hashes; optional signatures/provenance; reproducible builds as an explicit goal).
* **Hybrid-capable** (deterministic tools first + compressed knowledge pack + optional tiny model **only** for routing/classification/extraction).

**Goal:** “AI that ships like a plugin/library, not a cloud service.” The host app remains in control; the Cell is a dependable subsystem.

---

## 2) Non-goals

A Tasklet Cell is not:

* a general chatbot,
* an open-ended autonomous tool loop,
* a cloud-connected assistant,
* a component that silently rewrites its core behavior without passing conformance.

---

## 3) Core invariants (MUST)

These invariants define the artifact class.

### 3.1 Validity is proven

A Cell is **invalid unless it passes its embedded Verifier Pack under the target runner**.

### 3.2 Contracts at the boundary

Inputs and outputs are governed by **machine-checkable schemas** (default: JSON Schema). The runner validates:

* input **before** execution,
* output **after** execution.

### 3.3 Offline enforcement

The runner MUST enforce **network denial** by default.

### 3.4 Bounded resources

The runner MUST enforce hard bounds:

* wall-clock time,
* step budget (fuel/instruction limit where supported),
* memory ceiling,
* output size ceiling,
* max tool invocations.

### 3.5 Fail-closed behavior

Any violation (hash mismatch, schema violation, verifier failure, limit breach) MUST yield a deterministic error result, and execution MUST be rejected.

---

## 4) Artifact model

### 4.1 Two-layer structure

* **Cell bundle:** everything needed for one task.
* **Runner:** the enforcing host-side runtime that loads, validates, verifies, and executes Cells.

### 4.2 Preferred execution boundary (v0.1 default)

**WASM/WASI + Wasmtime** is the preferred sandbox boundary:

* explicit capability model (default deny),
* straightforward offline enforcement (no sockets/capability provided),
* deterministic step bounding via fuel.

A native shared-library Cell may be added as a later performance tier, but it increases cross-platform sandbox complexity.

---

## 5) Bundle format (v0.1) — MVP standard

**Container:** a `.cell` zip archive.

### 5.1 Required layout

```
<cell>.cell (zip)
  manifest.json
  hashes/sha256.json   # canonical v0.1 hash manifest
  schemas/input.schema.json
  schemas/output.schema.json
  verifier/tests.json  # canonical v0.1 verifier pack
  logic/logic.wasm
  licenses/THIRD_PARTY_NOTICES.txt
```

Compatibility notes:

* Some drafts use `hashes/sha256sums.txt` instead of `hashes/sha256.json`.
* Some drafts use `tests/golden/` (folder-per-case) or `verifier/cases.jsonl`.

**Runner recommendation:** support both `hashes/sha256.json` and `hashes/sha256sums.txt` for compatibility, while keeping `sha256.json` as the canonical MVP spec.

Optional directories:

```
  knowledge/
  model/
  provenance/
  sbom/
  signatures/
  tools/
  attestations/
```

### 5.2 Manifest essentials (v0.1 fields)

Minimum fields (names may follow the v0.1 spec in report 04):

* `cell_format_version`
* `id`, `name`, `version`
* `runner_compat`: `runner_api_version`, `execution_kind` ("wasi" | "native")
* `determinism`: `mode` ("strict" | "bounded" | "best_effort"), optional `seed`
* `limits`: `max_wall_ms`, `max_steps`, `max_memory_mb`, `max_output_bytes`, `max_tool_calls`
* `contracts`: `input_schema_path`, `output_schema_path`
* `verifier`: `tests_path`, `comparison.mode` (default: `canonical_json`), optional `float_tolerance`
* `capabilities`: `network=false`, `filesystem.preopens=[]`
* `licensing`: SPDX identifiers + notices path
* `integrity`: hash manifest path

### 5.3 Hashing and integrity

* `hashes/sha256.json` lists SHA-256 for every bundle file (except itself).
* The runner MUST fail closed on mismatch.
* Optional signatures/provenance may be added later (Cosign bundles, in-toto/SLSA, SBOM).

### 5.4 v0.2 profile (recommended next standard)

The v0.2 reports tighten interoperability by specifying:

* **Bundle container:** directory or archive with deterministic unpack rules.
* **Canonical bytes for signing:** JSON involved in signing SHOULD be canonicalized to avoid irrelevant key-order differences.
* **Hash list:** `hashes/sha256sums.txt` is accepted as an alternate canonical form.
* **Verifier pack:** `verifier/cases.jsonl` + `verifier/expected/` with per-case comparison modes.
* **Optional transport profile:** OCI/ORAS (Cells as OCI artifacts) as a future distribution channel.

### 5.5 Zip safety requirements (MUST)

To keep `.cell` bundles safe to open:

* Archives MUST NOT contain symlinks.
* Paths MUST be normalized and MUST NOT escape the bundle root (zip-slip defense).
* The runner MUST refuse bundles with duplicate or ambiguous paths after normalization.

### 5.6 Decompression and size limits (MUST)

To prevent zip bombs and resource exhaustion:

* The runner MUST enforce a maximum **total uncompressed size** for the bundle.
* The runner MUST enforce a maximum **per-file uncompressed size**.
* The runner MUST enforce a maximum **file count**.
* The runner MUST refuse archives with suspicious compression ratios beyond a configured threshold.

---

## 6) Verifier Pack

### 6.1 Golden tests are mandatory

The embedded Verifier Pack is the **validity anchor**: a Cell is invalid unless it passes all golden tests under the runner.

### 6.2 Format (v0.1 canonical)

`verifier/tests.json` is an array of test cases:

* each includes an `input` and an `expected_output`.

### 6.3 Format (v0.2 recommended)

`verifier/cases.jsonl` contains one JSON record per line and references expected outputs in `verifier/expected/`. Each case may declare a comparison mode:

* `canonical_json` (default for structured JSON)
* `exact_bytes` (byte-for-byte; binaries)
* `regex` (constrained text acceptance)
* `numeric_tolerance` (per-field epsilons for floats)

### 6.4 Alternate layouts (accepted for compatibility)

Some implementations may prefer `tests/golden/` folder-per-case layouts.

**Runner recommendation:** accept the canonical layout and at least one alternate layout to reduce spec drift.

### 6.5 Comparison policy

Default: **canonical JSON comparison** to avoid meaningless differences.

### 6.6 Runner conformance procedure

For each test case the runner MUST:

1. Validate input against the input schema.
2. Execute the Cell.
3. Validate output against the output schema.
4. Compare output to expected output under the declared comparison rules.

If any case fails, the Cell is **not valid** and MUST NOT execute in the host app.

### 6.7 Development hardening (recommended)

In addition to shipped goldens, use **property-based / fuzz testing** during development and CI to stress schema boundaries, tool interfaces, and invariants.

---

## 7) Runtime execution model (anti-agent-loop)

### 7.0 Runner load pipeline (fail-closed)

The runner should treat Cells as untrusted until proven valid. Recommended load order:

1. Open bundle (zip/directory) with safety checks.
2. Parse `manifest.json` and validate it against a runner-known manifest schema.
3. Verify file hashes (and optionally signatures/provenance).
4. Load input/output schemas and validate them.
5. Run the Verifier Pack in conformance mode.
6. Only then allow `run` execution.

### 7.0.1 Default I/O convention for WASI Cells

Recommended convention for WASI Cells:

* Runner provides **input JSON** via stdin.
* Cell emits **output JSON** via stdout.
* stderr is captured for debugging but MUST NOT affect deterministic outputs.

### 7.0.2 Deterministic error contract

On any failure, the runner returns a deterministic error object (no timestamps), for example:

* `BUNDLE_INVALID`, `HASH_MISMATCH`, `SCHEMA_INVALID`, `VERIFIER_FAILED`, `LIMIT_EXCEEDED`, `RUNTIME_TRAP`, `OUTPUT_SCHEMA_VIOLATION`.

### 7.0.3 Conformance vs run mode

* **Conformance mode** executes the full Verifier Pack and is the basis of “valid Cell” status.
* **Run mode** executes one input. A runner MAY cache verified status keyed by (bundle hash, runner version, policy). The safe default is to re-run conformance after changes.

### 7.1 Pipeline DAG, not infinite loops

Execution should be a bounded computation graph (a small pipeline), not an open-ended agent loop.

### 7.2 Hybrid pipeline (recommended)

(1) Validate + canonicalize input → (2) Deterministic tools-first transforms → (3) Retrieval from compressed knowledge pack (optional) → (4) Optional micro-model inference (classification/extraction only) → (5) Deterministic post-processing → (6) Validate output schema

### 7.3 Tool policy

* Tool invocations MUST be explicitly allowlisted.
* Tool I/O SHOULD be schema-validated.
* No shell execution by default.
* Treat any model-driven decisioning as untrusted: the runner enforces allowlists, parameter schemas, file access rules, and call limits.

---

## 8) Offline enforcement & bounds (cross-platform)

### 8.1 Tiered enforcement model (v0.2)

Runner MUST:

* achieve the **strongest feasible** enforcement on the current OS,
* **report the achieved enforcement level** (strong / best-effort / none),
* optionally refuse to run Cells when only weak enforcement is available.

### 8.2 Practical defaults

* **WASM-first**: easiest cross-platform way to get consistent offline + bounds.
* Native tier (later):

  * **Linux:** namespaces (incl. network namespaces), cgroup v2, seccomp.
  * **Windows:** Job Objects; AppContainer (no-network capability) where feasible; VM fallback (Windows Sandbox/Hyper-V style) for strongest isolation.
  * **macOS:** app sandbox entitlements for strongest native path; CLI sandboxing is weaker; VM fallback via Virtualization framework where needed.

### 8.3 Per-run enforcement report (required)

The runner SHOULD print (and optionally emit JSON) describing:

* offline enforcement level achieved,
* filesystem isolation level achieved,
* resource limits applied and whether OS-enforced or userland timeouts.

### 8.4 Determinism hardening for local ML runtimes

When a Cell includes any local ML component, strict reproducibility requires extra controls:

* **Strict mode:** mock time APIs to a fixed constant; route any RNG access through a deterministic PRNG seeded from `manifest.determinism.seed`.
* **Bounded mode:** permit minor numeric drift but require explicit tolerances in the verifier comparison rules.
* **Threading discipline:** prefer single-thread execution where runtimes are non-deterministic under parallelism; document chosen settings.
* **Inference config pinning:** store engine config (threads, seeds, quantization mode) in metadata or runner logs for auditability.

---

## 9) Hybrid intelligence (small but capable)

### 9.1 Principle

Move skill out of weights and into:

* deterministic transforms,
* compressed templates/SOPs,
* compact retrieval,
* tiny router/extractor models only when needed.

### 9.2 Knowledge pack

Recommended content:

* templates (subject lines, tone variants),
* SOPs/checklists (invoice fields, compliance reminders),
* phrase dictionaries (multilingual, domain terms),
* small approved examples.

Compression:

* dictionary-trained compression for repetitive templates,
* store indexes separately.

Retrieval:

* lexical (FTS) as a deterministic baseline,
* vector similarity only if needed.

### 9.3 Tiny model role (strictly limited)

Allowed roles:

* routing,
* classification,
* extraction.

Disallowed by default:

* free-form generation that cannot be reliably verified.

### 9.4 Size budget envelope

A 10–100 MB Cell payload is feasible if:

* manifest + schemas + hashes + tests: ~0.1–5 MB
* knowledge pack (compressed): ~5–60 MB
* router model: ~0–30 MB
* optional index: ~1–20 MB

### 9.5 Reference “high-capability” hybrid budget (~35 MB)

Illustrative example under 100 MB:

* Logic + deterministic tools (WASM): ~2 MB
* Search engine: ~1 MB
* Compressed knowledge pack (templates/rules): ~10 MB
* Embeddings model (quantized): ~5 MB
* Tiny ML model for extraction/classification (quantized): ~15 MB
* Verifier Pack (hundreds of goldens): ~2 MB

---

## 10) Native embedding in applications

### 10.0 Minimal CLI surface (recommended)

A reference runner SHOULD expose:

* `cell info <bundle>`
* `cell validate <bundle>`
* `cell test <bundle>`
* `cell run <bundle> --input <json>`

When MVP-5 (local-only learning) is enabled, the runner SHOULD also expose:

* `cell learn --feedback <json>`
* `cell show-learned`
* `cell reset-personalization`

All CLI commands SHOULD emit deterministic JSON results and exit non-zero on failure.

Recommended deterministic envelope (so tooling can parse reliably):

* success: `{ "ok": true, "data": { ... } }`
* failure: `{ "ok": false, "error": { "code": "...", "message": "..." } }`.

### 10.1 Integration philosophy: silent improvement

The UI is not a chat overlay. The host app calls the Cell as a subsystem.

Examples:

* Calculator silently fixes an expression and evaluates.
* Email client warns: “You wrote ‘attached’ but there is no attachment.”

### 10.2 SDK lifecycle API (canonical)

A minimal embedding API:

* `Cell_Load(bundle_path)`
* `Cell_Verify(cell_instance)`
* `Cell_Execute(cell_instance, input_json) -> output_json`

Host behavior:

* If verify fails, do not enable the feature.
* If run violates schema/limits, ignore output and keep normal app behavior.

### 10.3 Cell SDK helper (recommended)

Provide a small **Cell SDK** that standardizes:

* memory allocation / ABI for passing input/output bytes to `logic.wasm`,
* stable JSON encoding/decoding conventions,
* helper macros for deterministic WASM Cells.

---

## 11) Extension: Local-only Personal Learning Layer

This extends the reports with **per-user improvement without cloud and without global updates**.

### 11.1 Immutable Core + Personal Layer

* **Core Cell (immutable):** the shipped bundle that must always pass the Verifier Pack.
* **Personal Layer (mutable, local-only):** learns from the user’s interactions and corrections.

#### 11.1.1 Personal Layer binding (MUST)

To avoid applying stale learning to a changed core:

* Personal Layer state MUST be keyed to the **Core Cell identity** (recommended key: `cell.id + cell.version + bundle_hash`).
* If the Core changes, the runner MUST either migrate explicitly (with tests) or start with a fresh Personal Layer.

### 11.2 What “learning” means here

Learning MUST NOT rewrite the core. It is constrained to:

* approved templates/preferences,
* corrected mappings ("when I write X I mean Y"),
* ranked choices among safe outputs,
* retrieval memory of user-approved examples,
* optional tiny adapters only if bounded and rollbackable.

### 11.3 Update gate (MUST remain strict)

When the agent proposes a personalization update, the runner MUST:

* validate it against a **Personalization Schema**,
* re-run the **Core Verifier Pack** (must still pass),
* run a **Local Regression Pack** derived from the user’s approved history,
* enforce size/compute caps.

Only then may the personalization be applied.

### 11.4 User transparency loop

The agent periodically reports what it learned (plain-language rules). The user can Accept / Edit / Reject / Forget.

### 11.5 Bounded growth policy

Hard caps:

* max personalization storage (e.g., 5–50 MB),
* max learning compute per day,
* max proposals per day,
* keep the last N personalization snapshots for rollback.

### 11.6 Safety statement

This preserves the artifact class because:

* the core remains conformance-proven,
* the personal layer is bounded and revertible,
* validity still depends on the runner.

---

## 12) Security & red-team checklist

Threats to assume:

* bundle tampering,
* corrupted bundles,
* rollback attacks,
* schema drift,
* tool escalation,
* nondeterminism causing verifier failures.

Mitigations:

* mandatory SHA-256 hash verification,
* optional signatures/provenance and SBOM,
* monotonic version policy (anti-rollback),
* strict schema validation at all boundaries,
* tool allowlists + capability sandboxing,
* determinism modes + explicit tolerance rules.

Adjacent-but-not-equivalent references (conceptual clarity):

* **Model signature systems** describe model I/O but do not define an agent artifact with verifier packs, tool policies, bounds, and offline enforcement.
* **Formal neural verification tools** can prove properties of certain networks but do not define a full distribution/runtime artifact standard.

---

## 13) Licensing & free-forever constraints

Operational rules:

* Prefer permissive licenses for runner/tooling (MIT / Apache-2.0).
* Avoid copyleft traps for embedded distribution (AGPL) and restrictive model terms.
* Treat model weights as separately licensed artifacts.
* Include licensing metadata in the manifest; the validator may refuse missing or incompatible licensing.

Supply-chain attachments (v0.2 guidance):

* Optional SBOM: SPDX or CycloneDX in `sbom/`.
* Optional provenance attestations: in-toto / SLSA in `attestations/`.
* Optional secure update profile: if a distribution channel exists, include rollback-resistant metadata (TUF-style) to prevent silent reintroduction of vulnerable Cells.

---

## 14) Roadmap (Codex-friendly)

### MVP-0: Runner skeleton

* CLI: info / validate
* zip safety (zip-slip defense)
* deterministic error JSON

### MVP-1: Contracts + verifier harness

* JSON Schema validation
* run golden tests
* enable/disable Cells based on conformance

### MVP-2: Integrity

* sha256 verification mandatory
* optional signature hooks

### MVP-3: Offline + bounds

* WASI default deny
* Wasmtime fuel
* timeouts + output caps

### MVP-4: Native embedding demos

* calculator demo
* email demo
* include a small Cell SDK helper to standardize WASM I/O

### MVP-5: Local-only Personal Learning Layer

* personalization store + schema
* proposal gate + regression tests
* user-facing “what I learned” UI

---

## 15) Codex Execution Pack (vFinal)

Derived primarily from report 04 and extended to include MVP-5.

### 15.1 Master prompt (repo creation)

Use the master prompt from report 04 as the base, with these additions:

* Add a `personalization/` directory per Cell for local state (outside the signed bundle).
* Add a `personalization.schema.json` and a `local_regression/` harness.
* Add CLI commands:

  * `cell learn --feedback <json>`
  * `cell show-learned`
  * `cell reset-personalization`

### 15.2 Milestone prompts

Use report 04 milestone prompts for MVP-0..4. Add MVP-5 prompt:

* Implement Personal Layer storage + schema + gate.
* Demo: email Cell learns the user’s preferred closing phrase and applies it.

---

## 16) Cross-report anchor quotes (traceability)

Short quotes (for auditability) with explicit source naming.

### From 04. Sealed Offline Agent Module Report

* “A Cell is invalid unless it passes its embedded verifier pack under the target runner.”
* “Hybrid intelligence: deterministic tools first, a compressed knowledge pack, and only an optional tiny local model for routing/classification/extraction.”
* “MVP four: native embedding demos … Calculator … Email … ‘silent improvement’ integration pattern.”

### From 02. AGIF Security Report v0.2

* “True novelty is not any single primitive … but requiring them to cohere in a single offline artifact where passing a verifier pack is mandatory for validity and where the runner enforces ‘no network + resource bounds’ by default.”
* “Determinism must be formalized as levels (bit-exact vs canonical JSON vs tolerance-based numeric comparisons).”
* “Hybrid v0.2: deterministic tool-first pipeline + compressed knowledge pack (FTS + dictionary compression), with an optional micro-model used only for routing/classification—not open-ended generation.”
* “Cross-platform enforcement is tiered: achieve strongest feasible isolation, report it, optionally refuse weaker modes.”

### From 03. Gemini Offline Agent Module Plan

* “WASI default-deny capability model.”
* “Fuel consumption mechanics bound execution deterministically.”

### From 01. AGIF Offline Agent Artifact

* “Your novelty is the artifact standard + mandatory on-bundle verification + bounded runner policy.”

### From AGIF Desktop Security Report.md

* “Supply-chain tools secure artifacts, but they don’t define the behavioral contract-and-verifier semantics … merges supply-chain integrity with runtime behavioral verification.”

---

## 17) Glossary

* **Cell / Tasklet / Module:** sealed offline single-task artifact.
* **Runner:** enforces offline, limits, schema checks, verifier pack.
* **Verifier Pack:** golden tests shipped inside the artifact; must pass locally.
* **Contract:** input/output schema boundary.
* **Hybrid intelligence:** tools + compressed knowledge + tiny router/extractor model.
* **Personal Layer:** user-only local learning state, bounded and revertible.

---

## 18) Final identity

**AGIF Tasklet Cell:** firmware-grade single-task intelligence embedded inside an app—offline, bounded, contract-driven, self-verifying, and optionally locally self-improving per user.
