# AGENTS.override.md (Paper Evidence R1)

## Scope
- This initiative covers reproducible empirical evidence generation for Whitepaper R1.

## Canonical outputs
- All generated artifacts must live under:
  - `paper_evidence/<YYYY-MM-DD>/<git_short_sha>/`
- Do not write evidence outputs to `/tmp` when a repo-local path can be used.

## Required artifacts
- `env.json`
- `raw/`
- `summary.json`
- `summary.md`
- `paper_table.md`
- `reproduce.md`
- `figures/*.png`

## Reporting rule
- Never hide failing gates. Include failures in `known_gaps`.
