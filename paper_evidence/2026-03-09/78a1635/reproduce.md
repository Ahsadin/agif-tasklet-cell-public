# Reproducibility

This portable bundle is an audit/results pack for the clean `78a1635` anchor. It supports direct inspection of the reported outputs. Re-executing the evaluation requires a repository checkout at the same commit together with the local toolchain used by `make paper-eval` or `python3 tools/paper_eval/run_paper_eval.py`; the ZIP alone is not a self-contained rerun environment.

- Commit SHA: `78a163503ff570407c8c34065a5500c0e34e50d0`
- Short SHA: `78a1635`
- Branch: `HEAD`
- OS: `macOS-26.3.1-arm64-arm-64bit-Mach-O`
- CPU: `Apple M4`
- Python: `Python 3.14.3`
- Rust: `rustc 1.93.1 (01f6ddf75 2026-02-11)`
- Expected runtime (this run): ~71.6 minutes

## Repository Re-execution Commands
```bash
make paper-eval
# or
python3 tools/paper_eval/run_paper_eval.py
```

## Verify Output Hashes
```bash
cd paper_evidence/2026-03-09/78a1635
python3 - <<'PY'
import hashlib, json
from pathlib import Path
for rel in ['env.json','summary.json','summary.md','paper_table.md','reproduce.md']:
    p = Path(rel)
    print(rel, hashlib.sha256(p.read_bytes()).hexdigest())
PY
```

- Internet required: no (all suites run offline/local).
