#!/usr/bin/env python3
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Dict, List


DATEV_NS = {"d": "http://xml.datev.de/bedi/tps/ledger/v050"}
DOC_NS = {"d": "http://xml.datev.de/bedi/tps/document/v05.0"}


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


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


def parse_ledger_fields(raw_xml: bytes) -> Dict[str, str]:
    root = ET.fromstring(raw_xml)
    consolidate = root.find("d:consolidate", DATEV_NS)
    result = {
        "ledger_kind": "",
        "amount": "",
        "currency": "",
        "invoice_id": "",
        "tax": "",
        "counterparty": "",
    }
    if consolidate is not None:
        result["amount"] = str(consolidate.attrib.get("consolidatedAmount", "")).strip()
        result["currency"] = str(consolidate.attrib.get("consolidatedCurrencyCode", "")).strip()
        result["invoice_id"] = str(consolidate.attrib.get("consolidatedInvoiceId", "")).strip()

    payable = root.find(".//d:accountsPayableLedger", DATEV_NS)
    receivable = root.find(".//d:accountsReceivableLedger", DATEV_NS)
    ledger = payable if payable is not None else receivable
    if payable is not None:
        result["ledger_kind"] = "accountsPayableLedger"
    elif receivable is not None:
        result["ledger_kind"] = "accountsReceivableLedger"

    if ledger is not None:
        result["tax"] = (ledger.findtext("d:tax", default="", namespaces=DATEV_NS) or "").strip()
        supplier = (ledger.findtext("d:supplierName", default="", namespaces=DATEV_NS) or "").strip()
        customer = (ledger.findtext("d:customerName", default="", namespaces=DATEV_NS) or "").strip()
        result["counterparty"] = supplier if supplier != "" else customer
    return result


def build_summary(zip_path: Path) -> Dict[str, object]:
    month_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    ledger_kind_counts: Counter[str] = Counter()
    field_presence: Counter[str] = Counter()
    samples: List[Dict[str, str]] = []

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        manifest = parse_document_manifest(archive.read("document.xml")) if "document.xml" in names else {}
        xml_names = sorted(name for name in names if name.lower().endswith(".xml") and name != "document.xml")
        pdf_names = sorted(name for name in names if name.lower().endswith(".pdf"))
        pdf_stems = {Path(name).stem for name in pdf_names}
        xml_stems = {Path(name).stem for name in xml_names}

        for xml_name in xml_names:
            raw = archive.read(xml_name)
            fields = parse_ledger_fields(raw)
            guid = Path(xml_name).stem
            manifest_entry = manifest.get(guid, {})
            month = manifest_entry.get("month", "")
            label = manifest_entry.get("label", "")
            if month != "":
                month_counts[month] += 1
            if label != "":
                label_counts[label] += 1
            ledger_kind = fields.get("ledger_kind", "")
            if ledger_kind != "":
                ledger_kind_counts[ledger_kind] += 1
            for key, value in fields.items():
                if value != "":
                    field_presence[key] += 1
            if len(samples) < 8:
                samples.append(
                    {
                        "guid": guid,
                        "month": month,
                        "label": label,
                        "ledger_kind": ledger_kind,
                        "amount": fields.get("amount", ""),
                        "currency": fields.get("currency", ""),
                        "invoice_id": fields.get("invoice_id", ""),
                        "counterparty": fields.get("counterparty", ""),
                    }
                )

        return {
            "schema_version": "1.0.0",
            "zip_path": str(zip_path),
            "zip_sha256": file_sha256(zip_path),
            "zip_size_bytes": zip_path.stat().st_size,
            "file_counts": {
                "pdf": len(pdf_names),
                "xml": len(xml_names),
                "manifest_xml": 1 if "document.xml" in names else 0,
                "xml_without_pdf_pair": len(xml_stems - pdf_stems),
                "pdf_without_xml_pair": len(pdf_stems - xml_stems),
            },
            "document_labels": dict(sorted(label_counts.items())),
            "ledger_kinds": dict(sorted(ledger_kind_counts.items())),
            "months": dict(sorted(month_counts.items())),
            "field_presence_counts": dict(sorted(field_presence.items())),
            "samples": samples,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a local Lexware DATEV export ZIP without copying source files into the repo.")
    parser.add_argument("--zip", required=True, help="Path to the Lexware export ZIP")
    parser.add_argument("--out-json", required=True, help="Output JSON summary path")
    parser.add_argument("--out-md", required=True, help="Output Markdown summary path")
    args = parser.parse_args()

    zip_path = Path(args.zip).resolve()
    if not zip_path.exists():
        raise SystemExit(f"ERROR: ZIP not found: {zip_path}")

    summary = build_summary(zip_path)
    out_json = Path(args.out_json).resolve()
    out_md = Path(args.out_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Lexware Holdout Summary",
        "",
        f"- ZIP: `{summary['zip_path']}`",
        f"- SHA256: `{summary['zip_sha256']}`",
        f"- PDF files: `{summary['file_counts']['pdf']}`",
        f"- XML files: `{summary['file_counts']['xml']}`",
        f"- XML without PDF pair: `{summary['file_counts']['xml_without_pdf_pair']}`",
        f"- PDF without XML pair: `{summary['file_counts']['pdf_without_xml_pair']}`",
        "",
        "## Document labels",
    ]
    for key, value in summary["document_labels"].items():
        md_lines.append(f"- `{key}`: `{value}`")
    md_lines.extend(["", "## Ledger kinds"])
    for key, value in summary["ledger_kinds"].items():
        md_lines.append(f"- `{key}`: `{value}`")
    md_lines.extend(["", "## Months"])
    for key, value in summary["months"].items():
        md_lines.append(f"- `{key}`: `{value}`")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "data": {"summary_json": str(out_json), "summary_md": str(out_md)}}, separators=(",", ":")))


if __name__ == "__main__":
    main()
