# Changelog

## 2026-03-10
- Replaced the clean `78a1635` paper-evidence placeholder figure PNGs with real locally generated figure assets.
- Rebuilt both clean `78a1635` evidence ZIPs from the corrected anchor so the packaged bundle now contains the generated figures and no AppleDouble junk.
- Clarified that the portable evidence ZIP is an audit/results bundle, not a self-contained rerun environment.
- Clarified suite-runtime versus per-case A6 latency wording in the clean anchor summary.

## 2026-03-09
- Promoted the clean paper-evidence anchor to:
  - `paper_evidence/2026-03-09/78a1635/`
- Updated repo-facing paper evidence references so root docs stop pointing at the old `533c63e` baseline as canonical.
- Kept `533c63e` as historical failure context only.

## 2026-03-05
- Added paper-evidence orchestration and fail-closed benchmark tooling in the private prep repo used to generate the anchor.
- Added a 30-repeat default paper-evidence entrypoint in the private prep repo.
- Added README reproducibility notes for paper-evidence usage.
- Updated the paired A6 and hallucination benchmark harnesses in the private prep repo so paper-evidence runs write isolated raw outputs and summary metrics.
- Generated evidence pack by execution:
  - `paper_evidence/2026-03-05/bc85148/`
