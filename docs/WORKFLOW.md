# Public Repo Workflow

This file defines the maintenance rules for the public research snapshot.

## Documentation Is Canonical

- `docs/` is the public documentation source of truth.
- `docs/SPEC_vFinal.md` overrides conflicting summaries elsewhere in the repo.

## Change Scope

- Keep each change small and issue-scoped.
- Do not mix public research maintenance with private product work.

## Publication Hygiene

- Never add the private full-product tree or private product artifacts here.
- Never commit secrets, private keys, tokens, or generated ZIP bundles.
- Large release assets belong on GitHub Releases, not in git history.

## Evidence Handling

- The clean anchor at `paper_evidence/2026-03-09/78a1635/` is the canonical
  paper-support snapshot in this repo.
- Evidence documentation may be clarified for publication, but raw recorded
  outputs should not be silently rewritten.

## If Blocked

- Prefer the smallest safe fix that keeps the public repo accurate.
- If a change would expose private material or make an irreversible publication
  decision, stop and ask before proceeding.
