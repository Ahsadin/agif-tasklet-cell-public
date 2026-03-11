#!/usr/bin/env python3
import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


LOCALES = ("en-US", "de-DE", "es-ES")
SPLITS = ("train", "val", "test", "edge")

VENDORS = {
    "en-US": ["Acme Tools", "Delta Supplies", "Cafe Midtown", "Northwind Office"],
    "de-DE": ["Nord GmbH", "Taxi Berlin", "Buromarkt AG", "Kaffeehaus Mitte"],
    "es-ES": ["Proveedor SA", "Cafe Central", "Madrid Servicios", "Taller Azul"],
}


def money(value: float, locale: str) -> str:
    rounded = f"{value:.2f}"
    whole, frac = rounded.split(".")
    if locale == "en-US":
        return f"{whole}.{frac}"
    return f"{whole},{frac}"


def iso_day(seed_value: int) -> str:
    return (date(2025, 1, 1) + timedelta(days=seed_value % 365)).isoformat()


def format_invoice(record_id: str, locale: str, vendor: str, net: float, tax: float, total: float, invoice_number: str, include_subtotal: bool, include_tax: bool) -> str:
    if locale == "en-US":
        parts = [f"INVOICE {invoice_number}", vendor]
        if include_subtotal:
            parts.append(f"SUBTOTAL {money(net, locale)}")
        if include_tax:
            parts.append(f"TAX {money(tax, locale)}")
        parts.append(f"TOTAL {money(total, locale)}")
        return " ".join(parts)
    if locale == "de-DE":
        parts = [f"RECHNUNG {invoice_number}", vendor]
        if include_subtotal:
            parts.append(f"NETTO {money(net, locale)}")
        if include_tax:
            parts.append(f"MWST {money(tax, locale)}")
        parts.append(f"GESAMT {money(total, locale)}")
        return " ".join(parts)
    parts = [f"FACTURA {invoice_number}", vendor]
    if include_subtotal:
        parts.append(f"SUBTOTAL {money(net, locale)}")
    if include_tax:
        parts.append(f"IVA {money(tax, locale)}")
    parts.append(f"TOTAL {money(total, locale)}")
    return " ".join(parts)


def format_receipt(locale: str, vendor: str, total: float, tip: float, include_tip: bool) -> str:
    if locale == "en-US":
        parts = [f"RECEIPT {vendor}", f"TOTAL {money(total, locale)}"]
        if include_tip:
            parts.append(f"TIP {money(tip, locale)}")
        return " ".join(parts)
    if locale == "de-DE":
        parts = [f"QUITTUNG {vendor}", f"GESAMT {money(total, locale)}"]
        if include_tip:
            parts.append(f"TRINKGELD {money(tip, locale)}")
        return " ".join(parts)
    parts = [f"TICKET {vendor}", f"TOTAL {money(total, locale)}"]
    if include_tip:
        parts.append(f"PROPINA {money(tip, locale)}")
    return " ".join(parts)


def routing_label(doc_type: str) -> str:
    return "accounts_payable_invoice" if doc_type == "invoice" else "expense_receipt"


def currency_hint(locale: str) -> str:
    return "USD" if locale == "en-US" else "EUR"


def ledger_profile(doc_type: str) -> str:
    return "ap_default" if doc_type == "invoice" else "expense_default"


def build_record(split: str, idx: int, rng: random.Random, edge_mode: bool) -> Dict[str, object]:
    locale = LOCALES[idx % len(LOCALES)]
    doc_type = "invoice" if idx % 3 != 1 else "receipt"
    vendor = VENDORS[locale][idx % len(VENDORS[locale])]
    net = round(rng.uniform(12.0, 1800.0), 2)
    tax_rate = 0.19 if locale != "es-ES" else 0.21
    tax = round(net * tax_rate, 2) if doc_type == "invoice" else 0.0
    total = round(net + tax, 2) if doc_type == "invoice" else round(rng.uniform(5.0, 120.0), 2)
    tip = round(rng.uniform(1.0, 9.0), 2)
    include_subtotal = doc_type == "invoice" and (idx % 2 == 0)
    include_tax = doc_type == "invoice"
    invoice_number = f"{vendor.split()[0][:4].upper()}-{1000 + idx}"
    record_id = f"synthetic-{split.lower()}-{idx:06d}"
    invoice_date = iso_day(idx * 13)
    due_date = invoice_date if doc_type == "receipt" else iso_day((idx * 13) + 30)

    if doc_type == "invoice":
        ocr_text = format_invoice(
            record_id=record_id,
            locale=locale,
            vendor=vendor,
            net=net,
            tax=tax,
            total=total,
            invoice_number=invoice_number,
            include_subtotal=include_subtotal,
            include_tax=include_tax,
        )
        if edge_mode:
            ocr_text += f" REF {100 + idx} RATE {int(tax_rate * 100)}%"
    else:
        ocr_text = format_receipt(locale=locale, vendor=vendor, total=total, tip=tip, include_tip=edge_mode or idx % 2 == 0)
        invoice_number = ""

    return {
        "record_id": record_id,
        "split": split,
        "doc_type": doc_type,
        "locale": locale,
        "currency_hint": currency_hint(locale),
        "ocr_text": ocr_text,
        "account_context": {
            "ledger_profile": ledger_profile(doc_type),
            "cost_center": f"CC-{locale.replace('-', '')}",
            "vendor_hint": vendor,
        },
        "expected": {
            "routing_label": routing_label(doc_type),
            "extracted_fields": {
                "vendor_name": vendor,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "due_date": due_date,
                "currency": currency_hint(locale),
                "subtotal": total if doc_type == "receipt" else net,
                "tax_total": tax,
                "grand_total": total,
            },
        },
        "quality_flags": {
            "ocr_noise_level": "synthetic_edge" if edge_mode else "synthetic_clean",
            "review_status": "approved",
        },
        "provenance": {
            "source_id": "synthetic_numeric_v1",
            "labeler_id": "generator",
            "reviewer_id": "generator",
        },
    }


def generate_split(split: str, count: int, seed: int, edge_mode: bool) -> Iterable[Dict[str, object]]:
    rng = random.Random(seed)
    for idx in range(count):
        yield build_record(split=split, idx=idx, rng=rng, edge_mode=edge_mode)


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a deterministic synthetic invoice/receipt dataset for numeric extraction research.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--train-count", type=int, default=25000)
    parser.add_argument("--val-count", type=int, default=5000)
    parser.add_argument("--test-count", type=int, default=5000)
    parser.add_argument("--edge-count", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=4045)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    counts = {
        "train": args.train_count,
        "val": args.val_count,
        "test": args.test_count,
        "edge": args.edge_count,
    }

    for split in SPLITS:
        rows = generate_split(split=split, count=counts[split], seed=args.seed + len(split), edge_mode=(split == "edge"))
        write_jsonl(output_dir / f"{split}.jsonl", rows)

    manifest = {
        "schema_version": "1.0.0",
        "dataset_id": "synthetic_numeric_v1",
        "seed": args.seed,
        "counts": counts,
        "locales": list(LOCALES),
        "doc_types": ["invoice", "receipt"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "data": {"output_dir": str(output_dir), "manifest": str(output_dir / "manifest.json")}}, separators=(",", ":")))


if __name__ == "__main__":
    main()
