# PHASE MAP

Canonical phase-based issue tracking view.

## Summary

- Current MVP phase = MVP-6 (CLOSED)
- Remaining issues in current phase = 0
- Remaining MVP phases after current = 0
- Next issue (deterministic) = NONE (all indexed issues complete)

## Deterministic phase assignment

- `MVP-0`: `ISSUE-001` to `ISSUE-025`
- `MVP-1`: `ISSUE-026` to `ISSUE-028`
- `MVP-2`: `ISSUE-029` to `ISSUE-031`
- `MVP-2.5`: `ISSUE-032` to `ISSUE-034`
- `MVP-2.6`: `ISSUE-035`
- `MVP-3`: `ISSUE-036` to `ISSUE-040`
- `MVP-3.5`: `ISSUE-041` to `ISSUE-044`
- `MVP-4`: `ISSUE-045` to `ISSUE-048`
- `MVP-4.5`: `ISSUE-049`
- `MVP-4.6`: `ISSUE-050` to `ISSUE-051`
- `MVP-5`: `ISSUE-052` to `ISSUE-070`
- `MVP-6` (Prototype Proof (End-to-End)): `ISSUE-071` onward

## Issue map

| Issue | MVP Phase | Type | Short title | Status | Commit hash |
|---|---|---|---|---|---|
| ISSUE-001 | MVP-0 | docs-only | Create repository folder tree | DONE | f1b8583 |
| ISSUE-002 | MVP-0 | docs-only | Add repo hygiene files | DONE | f1b8583 |
| ISSUE-003 | MVP-0 | docs-only | Finalize hardening references and enforcement docs | DONE | 5e0929c |
| ISSUE-004 | MVP-0 | docs-only | Add AGENTS companion pointer files | DONE | f1b8583 |
| ISSUE-005 | MVP-0 | docs-only | Create canonical master spec index | DONE | f1b8583 |
| ISSUE-006 | MVP-0 | docs-only | Install canonical SPEC file | DONE | f1b8583 |
| ISSUE-007 | MVP-0 | docs-only | Add architecture, security, contracts docs | DONE | f1b8583 |
| ISSUE-008 | MVP-0 | docs-only | Add embedding and test strategy docs | DONE | f1b8583 |
| ISSUE-009 | MVP-0 | docs-only | Create phase plan MVP-0..MVP-5 | DONE | f1b8583 |
| ISSUE-010 | MVP-0 | docs-only | Create decisions log | DONE | f1b8583 |
| ISSUE-011 | MVP-0 | docs-only | Create workflow policy | DONE | f1b8583 |
| ISSUE-012 | MVP-0 | docs-only | Add anchor and setup prompts | DONE | f1b8583 |
| ISSUE-013 | MVP-0 | docs-only | Add parking prompt | DONE | f1b8583 |
| ISSUE-014 | MVP-0 | docs-only | Add snapshots templates | DONE | f1b8583 |
| ISSUE-015 | MVP-0 | docs-only | Add issues index | DONE | f1b8583 |
| ISSUE-016 | MVP-0 | docs-only | Add phase placeholder issue lists | DONE | f1b8583 |
| ISSUE-017 | MVP-0 | docs-only | Add docs README and docs changelog | DONE | f1b8583 |
| ISSUE-018 | MVP-0 | docs-only | Add setup plan document | DONE | f1b8583 |
| ISSUE-019 | MVP-0 | docs-only | Add GitHub issue template and CI placeholder | DONE | f1b8583 |
| ISSUE-020 | MVP-0 | docs-only | Setup verification and initial commit checkpoint | DONE | f1b8583 |
| ISSUE-021 | MVP-0 | docs-only | Close out Phase 0 and seed Phase 1 planning | DONE | ae81c23 |
| ISSUE-022 | MVP-0 | code | Scaffold runner CLI entry points (`cell info`, `cell validate`) | DONE | 6cb24a7 |
| ISSUE-023 | MVP-0 | code | Enforce safe bundle path handling (zip-slip + duplicate paths) | DONE | ecd6562 |
| ISSUE-024 | MVP-0 | code | Reject symlinks inside `.cell` bundles | DONE | 335a0bb |
| ISSUE-025 | MVP-0 | code | Add decompression safety limits | DONE | 6b48646 |
| ISSUE-026 | MVP-1 | code | Validate `manifest.json` against runner-known schema | DONE | 716ab95 |
| ISSUE-027 | MVP-1 | code | Add verifier pack harness (`verifier/tests.json`) | DONE | 8971725 |
| ISSUE-028 | MVP-1 | code | Enforce input/output schema validation order | DONE | 7915b7c |
| ISSUE-029 | MVP-2 | code | Implement hash integrity verification (`sha256.json` + compat `sha256sums.txt`) | DONE | 88fa48d |
| ISSUE-030 | MVP-2 | code | Add conformance gating for `run` mode | DONE | de7094a |
| ISSUE-031 | MVP-2 | docs-only | Seed concrete Phase 2 issue plan | DONE | d6c65aa |
| ISSUE-032 | MVP-2.5 | code | Add explicit `cell test <bundle>` conformance command | DONE | b58484d |
| ISSUE-033 | MVP-2.5 | code | Add verifier v0.2 layout compatibility (`cases.jsonl` + `expected/`) | DONE | 5d35ff7 |
| ISSUE-034 | MVP-2.5 | code | Implement per-case comparison modes for verifier results | DONE | ac91efd |
| ISSUE-035 | MVP-2.6 | code | Add integrity extension hooks for signatures/provenance | DONE | 8b625a1 |
| ISSUE-036 | MVP-3 | code | Enforce WASI offline default-deny policy in run path | DONE | 3ac1d83 |
| ISSUE-037 | MVP-3 | code | Enforce bounded execution limits (timeout, output bytes, tool calls) | DONE | a406e93 |
| ISSUE-038 | MVP-3 | code | Enforce fuel/step budget and memory ceiling policies | DONE | 915477c |
| ISSUE-039 | MVP-3 | code | Emit standardized enforcement report for validate/test/run | DONE | f53f4ee |
| ISSUE-040 | MVP-3 | code | Expand bounded-execution conformance fixtures and docs | DONE | a87b58d |
| ISSUE-041 | MVP-3.5 | docs-only | Seed concrete Phase 3 issue plan | DONE | 0f2bd04 |
| ISSUE-042 | MVP-3.5 | docs-only | Align MVP-4 demo docs with canonical Finance Desk scope | DONE | fd10291 |
| ISSUE-043 | MVP-3.5 | docs-only | Adopt Finance Desk as MVP-4 hero demo across docs/governance | DONE | 3991527 |
| ISSUE-044 | MVP-3.5 | docs-only | Define Cell SDK helper contract and ABI surface for Finance Desk flows | DONE | 9869ded |
| ISSUE-045 | MVP-4 | code | Build Finance Desk neural extractor reference Cell bundle and conformance fixtures | DONE | 0934983 |
| ISSUE-046 | MVP-4 | code | Build invoice completeness validator reference Cell bundle | DONE | 21b1f89 |
| ISSUE-047 | MVP-4 | code | Build VAT math checker reference Cell bundle | DONE | 929795b |
| ISSUE-048 | MVP-4 | code | Build duplicate detector Cell bundle and host trigger integration flow docs | DONE | 4249d14 |
| ISSUE-049 | MVP-4.5 | docs-only | Add gateway-path + replay conformance matrix for Finance Desk demos | DONE | d033de3 |
| ISSUE-050 | MVP-4.6 | docs-only | Close Phase 3 and seed Phase 4 planning handoff | DONE | a5221d5 |
| ISSUE-051 | MVP-4.6 | docs-only | Seed concrete Phase 4 issue plan | DONE | 5a03e86 |
| ISSUE-052 | MVP-5 | docs-only | Define personalization store schema and local regression harness contract | DONE | 38d94d9 |
| ISSUE-053 | MVP-5 | code | Add `cell learn --feedback <json>` CLI command scaffold | DONE | 4bf438f |
| ISSUE-054 | MVP-5 | code | Enforce Personal Layer binding to immutable core identity | DONE | a73c28b |
| ISSUE-055 | MVP-5 | code | Implement strict personalization update gate | DONE | 23f236c |
| ISSUE-056 | MVP-5 | code | Enforce bounded growth and rollback snapshot policy for Personal Layer | DONE | f4ca01d |
| ISSUE-057 | MVP-5 | code | Add `cell show-learned` transparency report command | DONE | d3b2df8 |
| ISSUE-058 | MVP-5 | code | Add `cell reset-personalization` with safe local reset behavior | DONE | 9ed04e5 |
| ISSUE-059 | MVP-5 | docs-only | Add Finance Desk personalization and regression conformance evidence | DONE | 4e5d927 |
| ISSUE-060 | MVP-5 | docs-only | Close Phase 4 and seed next planning handoff | DONE | e487f02 |
| ISSUE-061 | MVP-5 | docs-only | Seed concrete Phase 5 issue plan | DONE | - |
| ISSUE-062 | MVP-5 | docs-only | Define post-MVP-5 hardening scope and release gate | DONE | - |
| ISSUE-063 | MVP-5 | code | Enforce anti-rollback policy for core bundles | DONE | - |
| ISSUE-064 | MVP-5 | code | Enforce licensing completeness checks during validation | DONE | - |
| ISSUE-065 | MVP-5 | code | Add SBOM attachment policy checks and reporting | DONE | - |
| ISSUE-066 | MVP-5 | code | Add provenance attestation policy checks and reporting | DONE | - |
| ISSUE-067 | MVP-5 | docs-only | Document OCI/ORAS distribution compatibility profile | DONE | - |
| ISSUE-068 | MVP-5 | code | Add deterministic policy preset profiles for runner operations | DONE | - |
| ISSUE-069 | MVP-5 | docs-only | Build Phase 5 conformance evidence bundle for release readiness | DONE | - |
| ISSUE-070 | MVP-5 | docs-only | Close Phase 5 and seed next-phase handoff | DONE | - |
| ISSUE-071 | MVP-6 | docs-only | Back on track: redefine Phase 6 as prototype proof + runnability gate | DONE | - |
| ISSUE-072 | MVP-6 | code | Add runnable finance example inputs and expected output fixtures | DONE | - |
| ISSUE-073 | MVP-6 | code | Ensure neural extractor run path returns schema-valid non-placeholder output | DONE | - |
| ISSUE-074 | MVP-6 | code | Ensure deterministic finance validator cells run and goldens pass | DONE | - |
| ISSUE-075 | MVP-6 | code | Implement replay record/replay reproduction proof with strict or tolerance-pass mode | DONE | - |
| ISSUE-076 | MVP-6 | code | Demonstrate bounded learn/show-learned/reset flow with observable change | DONE | - |
| ISSUE-077 | MVP-6 | docs+script | Add one-command Phase 6 prototype runbook script and summary output | DONE | - |
| ISSUE-078 | MVP-6 | docs-only | Publish Phase 6 prototype evidence package snapshot | DONE | - |
| ISSUE-079 | MVP-6 | docs-only | Close Phase 6 only after prototype proof gate is satisfied | DONE | - |
