#!/usr/bin/env python3
"""Prepare v4 transformer dataset inputs with strict contract validation.

This utility validates A1-like split files, then writes normalized transformer-ready
JSONL records with deterministic text and label mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

SPLITS: Tuple[str, ...] = ("train", "val", "test", "edge")
REQUIRED_TOP_KEYS: Tuple[str, ...] = (
    "record_id",
    "split",
    "doc_type",
    "locale",
    "currency_hint",
    "ocr_text",
    "account_context",
    "expected",
    "quality_flags",
    "provenance",
)
REQUIRED_EXTRACTED_KEYS: Tuple[str, ...] = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax_total",
    "grand_total",
)
ROUTING_LABEL_TO_ID: Dict[str, int] = {
    "accounts_payable_invoice": 0,
    "expense_receipt": 1,
    "other_finance_doc": 2,
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def ensure_non_empty_string(obj: Dict[str, Any], key: str, path: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or value.strip() == "":
        fail(f"{path}.{key} must be non-empty string")
    return value


def ensure_object(obj: Dict[str, Any], key: str, path: str) -> Dict[str, Any]:
    value = obj.get(key)
    if not isinstance(value, dict):
        fail(f"{path}.{key} must be object")
    return value


def ensure_number(obj: Dict[str, Any], key: str, path: str) -> float:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{path}.{key} must be number")
    return float(value)


def validate_record(record: Dict[str, Any], expected_split: str, line_no: int, source: Path) -> str:
    path = f"{source.name}:line[{line_no}]"

    for key in REQUIRED_TOP_KEYS:
        if key not in record:
            fail(f"{path}.{key} is required")

    record_id = ensure_non_empty_string(record, "record_id", path)

    split = ensure_non_empty_string(record, "split", path)
    if split not in SPLITS:
        fail(f"{path}.split must be one of {SPLITS}")
    if split != expected_split:
        fail(f"{path}.split={split} does not match file split={expected_split}")

    ensure_non_empty_string(record, "doc_type", path)
    ensure_non_empty_string(record, "locale", path)
    ensure_non_empty_string(record, "currency_hint", path)
    ensure_non_empty_string(record, "ocr_text", path)

    account_context = ensure_object(record, "account_context", path)
    ensure_non_empty_string(account_context, "ledger_profile", f"{path}.account_context")
    ensure_non_empty_string(account_context, "cost_center", f"{path}.account_context")

    expected = ensure_object(record, "expected", path)
    ensure_non_empty_string(expected, "routing_label", f"{path}.expected")
    extracted = ensure_object(expected, "extracted_fields", f"{path}.expected")

    for key in REQUIRED_EXTRACTED_KEYS:
        if key not in extracted:
            fail(f"{path}.expected.extracted_fields.{key} is required")

    for key in ("vendor_name", "invoice_number", "invoice_date", "due_date", "currency"):
        value = extracted.get(key)
        if not isinstance(value, str):
            fail(f"{path}.expected.extracted_fields.{key} must be string")

    for key in ("subtotal", "tax_total", "grand_total"):
        ensure_number(extracted, key, f"{path}.expected.extracted_fields")

    quality_flags = ensure_object(record, "quality_flags", path)
    ensure_non_empty_string(quality_flags, "ocr_noise_level", f"{path}.quality_flags")
    review_status = ensure_non_empty_string(quality_flags, "review_status", f"{path}.quality_flags")
    if review_status not in {"approved", "needs_review"}:
        fail(f"{path}.quality_flags.review_status must be approved or needs_review")

    provenance = ensure_object(record, "provenance", path)
    ensure_non_empty_string(provenance, "source_id", f"{path}.provenance")
    ensure_non_empty_string(provenance, "labeler_id", f"{path}.provenance")
    ensure_non_empty_string(provenance, "reviewer_id", f"{path}.provenance")

    return record_id


def duplicate_key(record: Dict[str, Any]) -> str:
    payload = {
        "ocr_text": str(record.get("ocr_text", "")),
        "expected": record.get("expected", {}),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def normalized_ocr_text(record: Dict[str, Any]) -> str:
    text = str(record.get("ocr_text", "")).strip().lower()
    return " ".join(text.split())


def load_split(path: Path, split: str) -> List[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        fail(f"split file missing: {path}")

    rows: List[Dict[str, Any]] = []
    seen_ids = set()
    seen_dup_keys = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if line == "":
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as err:
                fail(f"invalid JSON in {path} line {line_no}: {err}")
            if not isinstance(record, dict):
                fail(f"{path.name}:line[{line_no}] must be JSON object")
            record_id = validate_record(record, expected_split=split, line_no=line_no, source=path)
            if record_id in seen_ids:
                fail(f"duplicate record_id in {path.name}: {record_id}")
            seen_ids.add(record_id)
            dup = duplicate_key(record)
            if dup in seen_dup_keys:
                fail(f"duplicate ocr_text+expected in {path.name}")
            seen_dup_keys.add(dup)
            rows.append(record)

    if len(rows) == 0:
        fail(f"split file has no records: {path}")

    return rows


def validate_cross_split_integrity(split_rows: Dict[str, List[Dict[str, Any]]]) -> None:
    seen_record_ids: Dict[str, str] = {}
    seen_dup_keys: Dict[str, str] = {}
    text_sets: Dict[str, set] = {split: set() for split in SPLITS}

    for split in SPLITS:
        for record in split_rows[split]:
            record_id = str(record["record_id"])
            dup_key = duplicate_key(record)
            norm_text = normalized_ocr_text(record)

            prev_split = seen_record_ids.get(record_id)
            if prev_split is not None:
                fail(f"record_id leakage across splits: {record_id} in {prev_split} and {split}")
            seen_record_ids[record_id] = split

            prev_dup_split = seen_dup_keys.get(dup_key)
            if prev_dup_split is not None:
                fail(f"duplicate ocr_text+expected leakage across splits: {prev_dup_split} and {split}")
            seen_dup_keys[dup_key] = split

            if norm_text in text_sets[split]:
                fail(f"duplicate normalized ocr_text inside split: {split}")
            text_sets[split].add(norm_text)

    leakage_train_test = text_sets["train"].intersection(text_sets["test"])
    if leakage_train_test:
        fail("train/test normalized text leakage detected")


def _build_transformer_text(record: Dict[str, Any]) -> str:
    account_context = record["account_context"]
    pieces = [
        f"doc_type:{record['doc_type'].strip().lower()}",
        f"locale:{record['locale'].strip()}",
        f"currency_hint:{record['currency_hint'].strip().upper()}",
        f"ledger_profile:{str(account_context.get('ledger_profile', '')).strip()}",
        f"cost_center:{str(account_context.get('cost_center', '')).strip()}",
        f"vendor_hint:{str(account_context.get('vendor_hint', '')).strip()}",
        f"ocr:{record['ocr_text'].strip()}",
    ]
    return " | ".join(pieces)


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    routing_label = str(record["expected"]["routing_label"]).strip()
    label_id = ROUTING_LABEL_TO_ID.get(routing_label)
    if label_id is None:
        fail(f"unsupported expected.routing_label for transformer prep: {routing_label}")

    extracted = record["expected"]["extracted_fields"]
    normalized = {
        "record_id": str(record["record_id"]),
        "split": str(record["split"]),
        "text": _build_transformer_text(record),
        "label": routing_label,
        "label_id": int(label_id),
        "targets": {
            "routing_label": routing_label,
            "vat_rate_proxy": round(float(extracted["tax_total"]) / float(max(extracted["subtotal"], 0.01)), 6),
            "extracted_fields": {
                "vendor_name": str(extracted["vendor_name"]),
                "invoice_number": str(extracted["invoice_number"]),
                "invoice_date": str(extracted["invoice_date"]),
                "due_date": str(extracted["due_date"]),
                "currency": str(extracted["currency"]),
                "subtotal": float(extracted["subtotal"]),
                "tax_total": float(extracted["tax_total"]),
                "grand_total": float(extracted["grand_total"]),
            },
        },
    }
    normalized["sample_hash"] = hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()
    return normalized


def write_normalized_splits(output_dir: Path, split_rows: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Path]:
    normalized_dir = output_dir / "normalized_jsonl"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    output_paths: Dict[str, Path] = {}
    for split in SPLITS:
        rows = split_rows[split]
        path = normalized_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in rows:
                normalized = normalize_record(record)
                handle.write(canonical_json(normalized) + "\n")
        output_paths[split] = path
    return output_paths


def build_dataset_manifest(
    dataset_id: str,
    dataset_version: str,
    split_paths: Dict[str, Path],
    split_rows: Dict[str, List[Dict[str, Any]]],
    normalized_paths: Dict[str, Path],
) -> Dict[str, Any]:
    class_distribution: Dict[str, int] = {}
    locale_distribution: Dict[str, int] = {}
    source_batches: Dict[str, int] = {}
    quality_summary = {"approved_count": 0, "needs_review_count": 0}

    for split in SPLITS:
        for record in split_rows[split]:
            doc_type = str(record.get("doc_type", ""))
            locale = str(record.get("locale", ""))
            source_id = str(record.get("provenance", {}).get("source_id", ""))
            review_status = str(record.get("quality_flags", {}).get("review_status", ""))

            class_distribution[doc_type] = class_distribution.get(doc_type, 0) + 1
            locale_distribution[locale] = locale_distribution.get(locale, 0) + 1
            source_batches[source_id] = source_batches.get(source_id, 0) + 1

            if review_status == "approved":
                quality_summary["approved_count"] += 1
            elif review_status == "needs_review":
                quality_summary["needs_review_count"] += 1

    hashes: Dict[str, str] = {}
    for split, path in split_paths.items():
        hashes[f"input/{split}.jsonl"] = file_sha256(path)
    for split, path in normalized_paths.items():
        hashes[f"normalized/{split}.jsonl"] = file_sha256(path)

    created_at = os.environ.get("AGIF_DATASET_CREATED_AT", "1970-01-01T00:00:00Z").strip() or "1970-01-01T00:00:00Z"
    return {
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "created_at": created_at,
        "schema_version": "1.0.0",
        "record_counts": {split: len(rows) for split, rows in split_rows.items()},
        "class_distribution": class_distribution,
        "locale_distribution": locale_distribution,
        "source_batches": source_batches,
        "quality_summary": quality_summary,
        "hashes": hashes,
    }


def write_dataset_manifest(output_dir: Path, manifest: Dict[str, Any]) -> Path:
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def write_checksums(output_dir: Path, files: Dict[str, Path]) -> Path:
    checksums_path = output_dir / "checksums.sha256"
    lines = []
    for label in sorted(files.keys()):
        lines.append(f"{file_sha256(files[label])}  {label}")
    checksums_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksums_path


def write_preparation_index(
    output_dir: Path,
    dataset_id: str,
    dataset_version: str,
    split_paths: Dict[str, Path],
    split_rows: Dict[str, List[Dict[str, Any]]],
    normalized_paths: Dict[str, Path],
    manifest_path: Path,
    checksums_path: Path,
) -> Path:
    label_distribution: Dict[str, int] = {}
    for split in SPLITS:
        for record in split_rows[split]:
            label = str(record["expected"]["routing_label"])
            label_distribution[label] = label_distribution.get(label, 0) + 1

    index_payload = {
        "command": "v4_prepare_transformer_dataset",
        "mode": "normalized_jsonl_v1",
        "dataset_id": dataset_id,
        "dataset_version": dataset_version,
        "record_counts": {split: len(rows) for split, rows in split_rows.items()},
        "input_files": {split: str(path) for split, path in split_paths.items()},
        "input_hashes": {split: file_sha256(path) for split, path in split_paths.items()},
        "normalized_files": {split: str(path) for split, path in normalized_paths.items()},
        "normalized_hashes": {split: file_sha256(path) for split, path in normalized_paths.items()},
        "label_distribution": label_distribution,
        "label_map": ROUTING_LABEL_TO_ID,
        "manifest_path": str(manifest_path),
        "manifest_hash": file_sha256(manifest_path),
        "checksums_path": str(checksums_path),
        "checksums_hash": file_sha256(checksums_path),
    }
    index_payload["preparation_hash"] = hashlib.sha256(
        canonical_json(index_payload).encode("utf-8")
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "v4_dataset_prepare_index.json"
    index_path.write_text(
        json.dumps(index_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare v4 transformer dataset (skeleton)")
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--edge", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    split_paths: Dict[str, Path] = {
        "train": Path(args.train).resolve(),
        "val": Path(args.val).resolve(),
        "test": Path(args.test).resolve(),
        "edge": Path(args.edge).resolve(),
    }
    split_rows = {split: load_split(path, split) for split, path in split_paths.items()}
    validate_cross_split_integrity(split_rows)
    output_dir = Path(args.output_dir).resolve()
    normalized_paths = write_normalized_splits(output_dir=output_dir, split_rows=split_rows)
    manifest_payload = build_dataset_manifest(
        dataset_id=args.dataset_id,
        dataset_version=args.dataset_version,
        split_paths=split_paths,
        split_rows=split_rows,
        normalized_paths=normalized_paths,
    )
    manifest_path = write_dataset_manifest(output_dir=output_dir, manifest=manifest_payload)
    checksum_files = {f"input_{split}.jsonl": path for split, path in split_paths.items()}
    checksum_files.update({f"normalized_{split}.jsonl": path for split, path in normalized_paths.items()})
    checksum_files["manifest.json"] = manifest_path
    checksums_path = write_checksums(output_dir=output_dir, files=checksum_files)

    index_path = write_preparation_index(
        output_dir=output_dir,
        dataset_id=args.dataset_id,
        dataset_version=args.dataset_version,
        split_paths=split_paths,
        split_rows=split_rows,
        normalized_paths=normalized_paths,
        manifest_path=manifest_path,
        checksums_path=checksums_path,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "data": {
                    "command": "v4_prepare_transformer_dataset",
                    "mode": "normalized_jsonl_v1",
                    "dataset_id": args.dataset_id,
                    "dataset_version": args.dataset_version,
                    "output_index": str(index_path),
                    "normalized_files": {split: str(path) for split, path in normalized_paths.items()},
                    "manifest_path": str(manifest_path),
                    "checksums_path": str(checksums_path),
                    "record_counts": {split: len(rows) for split, rows in split_rows.items()},
                },
            },
            sort_keys=False,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
