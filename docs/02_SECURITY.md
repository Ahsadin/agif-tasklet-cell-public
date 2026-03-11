# 02 Security

## Threat model

- Bundle tampering.
- Zip-slip and zip bombs.
- Schema drift.
- Unbounded runtime behavior.
- Unauthorized network or filesystem access.

## Required mitigations

- SHA-256 verification fail-closed.
- Zip safety checks: path normalization, symlink ban, duplicate/ambiguous path rejection.
- Decompression limits: total uncompressed size, per-file max, file-count max, compression-ratio threshold.
- Offline enforcement by default with capability deny.
- Hard resource limits: wall time, steps/fuel, memory, output bytes, tool call count.

## Integrity and signing roadmap

- v0.1: mandatory hashes.
- v0.2+: optional signatures/provenance and SBOM attachments.
