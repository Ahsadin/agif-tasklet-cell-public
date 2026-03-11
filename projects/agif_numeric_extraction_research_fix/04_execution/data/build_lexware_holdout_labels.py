#!/usr/bin/env python3
"""Build a local-only label manifest from a Lexware DATEV export ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, Optional


DATEV_NS = {"d": "http://xml.datev.de/bedi/tps/ledger/v050"}
DOC_NS = {"d": "http://xml.datev.de/bedi/tps/document/v05.0"}
MONEY_Q = Decimal("0.01")


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_decimal(raw: str) -> Optional[Decimal]:
    text = str(raw).strip().replace(",", ".")
    if text == "":
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def money_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value.quantize(MONEY_Q, rounding=ROUND_HALF_UP))


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def parse_document_manifest(raw_xml: bytes) -> Dict[str, Dict[str, str]]:
    root = ET.fromstring(raw_xml)
    docs: Dict[str, Dict[str, str]] = {}
    for doc in root.findall(".//d:document", DOC_NS):
        guid = str(doc.attrib.get("guid", "")).strip()
        if guid == "":
            continue
        info = {"month": "", "label": "", "xml_name": "", "pdf_name": ""}
        for ext in doc.findall("d:extension", DOC_NS):
            xsi_type = str(ext.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")).strip()
            if "Ledger" in xsi_type:
                info["xml_name"] = str(ext.attrib.get("datafile", "")).strip()
                for prop in ext.findall("d:property", DOC_NS):
                    key = str(prop.attrib.get("key", "")).strip()
                    value = str(prop.attrib.get("value", "")).strip()
                    if key == "1":
                        info["month"] = value
                    elif key == "3":
                        info["label"] = value
            elif xsi_type == "File":
                info["pdf_name"] = str(ext.attrib.get("name", "")).strip()
        docs[guid] = info
    return docs


def first_text(node: ET.Element, paths: Iterable[str]) -> str:
    for path in paths:
        value = node.findtext(path, default="", namespaces=DATEV_NS)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def derive_amounts(gross_total: Decimal, tax_rate: Optional[Decimal]) -> Dict[str, object]:
    if tax_rate is None or tax_rate <= Decimal("0"):
        return {
            "subtotal": money_float(gross_total),
            "tax_total": 0.0,
            "derivation_source": "gross_only",
        }
    divisor = Decimal("1.0") + (tax_rate / Decimal("100.0"))
    subtotal = quantize_money(gross_total / divisor)
    tax_total = quantize_money(gross_total - subtotal)
    return {
        "subtotal": money_float(subtotal),
        "tax_total": money_float(tax_total),
        "derivation_source": "gross_plus_tax_rate",
    }


def parse_ledger_document(guid: str, raw_xml: bytes, manifest_entry: Dict[str, str], pdf_raw: bytes) -> Dict[str, object]:
    root = ET.fromstring(raw_xml)
    consolidate = root.find("d:consolidate", DATEV_NS)
    if consolidate is None:
        raise ValueError(f"{guid}: missing consolidate block")

    ledger = root.find(".//d:accountsPayableLedger", DATEV_NS)
    ledger_kind = "accountsPayableLedger"
    if ledger is None:
        ledger = root.find(".//d:accountsReceivableLedger", DATEV_NS)
        ledger_kind = "accountsReceivableLedger"
    if ledger is None:
        raise ValueError(f"{guid}: missing payable/receivable ledger")

    gross_total = parse_decimal(str(consolidate.attrib.get("consolidatedAmount", "")).strip())
    if gross_total is None:
        raise ValueError(f"{guid}: missing consolidatedAmount")
    currency = str(consolidate.attrib.get("consolidatedCurrencyCode", "")).strip()
    invoice_id = str(consolidate.attrib.get("consolidatedInvoiceId", "")).strip()
    consolidated_date = str(consolidate.attrib.get("consolidatedDate", "")).strip()
    tax_rate = parse_decimal(first_text(ledger, ("d:tax",)))
    derived = derive_amounts(gross_total, tax_rate)

    return {
        "document_id": guid,
        "month": manifest_entry.get("month", ""),
        "document_label": manifest_entry.get("label", ""),
        "ledger_kind": ledger_kind,
        "xml_name": manifest_entry.get("xml_name", ""),
        "pdf_name": manifest_entry.get("pdf_name", ""),
        "source_hashes": {
            "xml_sha256": sha256_bytes(raw_xml),
            "pdf_sha256": sha256_bytes(pdf_raw),
        },
        "extracted": {
            "gross_total": money_float(gross_total),
            "currency": currency,
            "invoice_id": invoice_id,
            "document_date": consolidated_date or first_text(ledger, ("d:date",)),
            "due_date": first_text(ledger, ("d:dueDate",)),
            "counterparty": first_text(ledger, ("d:supplierName", "d:customerName")),
            "tax_rate": money_float(tax_rate),
            "subtotal": derived["subtotal"],
            "tax_total": derived["tax_total"],
        },
        "provenance": {
            "source": "lexware_datev_export_zip",
            "numeric_derivation_source": derived["derivation_source"],
            "gross_total_source": "xml_consolidatedAmount",
            "tax_rate_source": "xml_tax",
            "privacy": "local_only_private_holdout",
        },
    }


def build_labels(zip_path: Path) -> Dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        manifest = parse_document_manifest(archive.read("document.xml")) if "document.xml" in names else {}

        rows = []
        for guid, manifest_entry in sorted(manifest.items()):
            xml_name = manifest_entry.get("xml_name", "")
            pdf_name = manifest_entry.get("pdf_name", "")
            if xml_name == "" or pdf_name == "":
                continue
            if xml_name not in names or pdf_name not in names:
                continue
            xml_raw = archive.read(xml_name)
            pdf_raw = archive.read(pdf_name)
            rows.append(parse_ledger_document(guid, xml_raw, manifest_entry, pdf_raw))

    label_counts: Dict[str, int] = {}
    for row in rows:
        label = str(row.get("document_label", ""))
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "schema_version": "1.0.0",
        "zip_path": str(zip_path),
        "zip_sha256": sha256_bytes(zip_path.read_bytes()),
        "row_count": len(rows),
        "document_labels": dict(sorted(label_counts.items())),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a private local label manifest from a Lexware export ZIP.")
    parser.add_argument("--zip", required=True, help="Path to the Lexware export ZIP")
    parser.add_argument("--out-jsonl", required=True, help="Output JSONL path for local label rows")
    parser.add_argument("--out-summary", required=True, help="Output JSON summary path")
    args = parser.parse_args()

    zip_path = Path(args.zip).resolve()
    if not zip_path.exists() or not zip_path.is_file():
        raise SystemExit(f"ERROR: ZIP not found: {zip_path}")

    payload = build_labels(zip_path)
    out_jsonl = Path(args.out_jsonl).resolve()
    out_summary = Path(args.out_summary).resolve()
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    out_summary.parent.mkdir(parents=True, exist_ok=True)

    with out_jsonl.open("w", encoding="utf-8") as handle:
        for row in payload["rows"]:
            handle.write(canonical_json(row) + "\n")

    summary = {
        "schema_version": payload["schema_version"],
        "zip_path": payload["zip_path"],
        "zip_sha256": payload["zip_sha256"],
        "row_count": payload["row_count"],
        "document_labels": payload["document_labels"],
        "out_jsonl": str(out_jsonl),
    }
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "data": summary}, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
