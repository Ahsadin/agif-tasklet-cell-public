"""Fail-closed local suggestions store for v5 proactive agent."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SUGGESTIONS_PATH = Path("personalization/suggestions.json")
MAX_ACTIVE_SUGGESTIONS = 50

ALLOWED_SUGGESTION_TYPES = {
    "vat_rate_inconsistency",
    "import_volume_spike",
    "recurring_correction_pattern",
}
ALLOWED_SEVERITY = {"HIGH", "MEDIUM", "LOW"}
SEVERITY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


class SuggestionsStoreError(RuntimeError):
    """Base suggestions-store error."""


class SuggestionsValidationError(SuggestionsStoreError):
    """Raised when suggestion payload is schema-invalid."""


class SuggestionsStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else DEFAULT_SUGGESTIONS_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap_if_missing()

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _bootstrap_if_missing(self) -> None:
        if self.path.exists():
            return
        self._write_atomic([])

    def _backup_corrupt_file(self) -> None:
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.path.with_name(f"{self.path.stem}.corrupt-{stamp}{self.path.suffix}")
        try:
            self.path.replace(backup)
        except Exception:
            # Fail-closed: if backup move fails, continue by overwriting the primary file.
            pass

    def _read_validated(self) -> List[Dict[str, Any]]:
        self._bootstrap_if_missing()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise SuggestionsValidationError("suggestions file must be JSON array")
            return [self._normalize_suggestion(item) for item in raw]
        except Exception:
            # Fail-closed recovery path for parse/schema failures.
            self._backup_corrupt_file()
            self._write_atomic([])
            return []

    def _write_atomic(self, rows: List[Dict[str, Any]]) -> None:
        payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        tmp_path = self.path.with_name(f"{self.path.name}.tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self.path)

    def load_all(self) -> List[Dict[str, Any]]:
        return self._read_validated()

    def get_active(self) -> List[Dict[str, Any]]:
        rows = self._read_validated()
        active = [item for item in rows if bool(item.get("dismissed")) is False]
        active.sort(key=self._sort_key, reverse=True)
        return active

    def count_active(self) -> int:
        return len(self.get_active())

    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        target = self._require_non_empty_string(suggestion_id, "id")
        rows = self._read_validated()
        updated = False
        for row in rows:
            if row.get("id") == target and bool(row.get("dismissed")) is False:
                row["dismissed"] = True
                updated = True
                break
        if updated:
            self._write_atomic(rows)
        return updated

    def upsert_suggestions(self, suggestions: List[Dict[str, Any]]) -> Dict[str, int]:
        if not isinstance(suggestions, list):
            raise SuggestionsValidationError("suggestions must be array")

        normalized_new = [self._normalize_suggestion(item) for item in suggestions]
        existing_rows = self._read_validated()
        by_id: Dict[str, Dict[str, Any]] = {str(item["id"]): item for item in existing_rows}

        inserted = 0
        updated = 0
        for item in normalized_new:
            sid = str(item["id"])
            prev = by_id.get(sid)
            if prev is None:
                by_id[sid] = item
                inserted += 1
                continue

            merged = dict(item)
            # Preserve dismissed state once user dismisses a suggestion.
            merged["dismissed"] = bool(prev.get("dismissed", False))
            by_id[sid] = merged
            updated += 1

        merged_rows = list(by_id.values())
        merged_rows.sort(key=self._sort_key, reverse=True)
        trimmed_rows, auto_dismissed = self._enforce_active_cap(merged_rows)
        self._write_atomic(trimmed_rows)

        return {
            "inserted": inserted,
            "updated": updated,
            "auto_dismissed": auto_dismissed,
            "active_count": len([item for item in trimmed_rows if bool(item.get("dismissed")) is False]),
            "total_count": len(trimmed_rows),
        }

    def _enforce_active_cap(self, rows: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
        active_rows = [row for row in rows if bool(row.get("dismissed")) is False]
        if len(active_rows) <= MAX_ACTIVE_SUGGESTIONS:
            return rows, 0

        overflow = len(active_rows) - MAX_ACTIVE_SUGGESTIONS
        # Oldest active entries auto-dismiss first.
        active_rows.sort(
            key=lambda row: (
                self._created_utc_sortable(str(row.get("created_utc", ""))),
                str(row.get("id", "")),
            )
        )
        ids_to_dismiss = {str(item.get("id")) for item in active_rows[:overflow]}

        auto_dismissed = 0
        output: List[Dict[str, Any]] = []
        for row in rows:
            copy = dict(row)
            if bool(copy.get("dismissed")) is False and str(copy.get("id")) in ids_to_dismiss:
                copy["dismissed"] = True
                auto_dismissed += 1
            output.append(copy)
        return output, auto_dismissed

    def _normalize_suggestion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise SuggestionsValidationError("suggestion must be object")
        suggestion_id = self._require_non_empty_string(payload.get("id"), "id")
        created_utc = self._require_non_empty_string(payload.get("created_utc"), "created_utc")
        suggestion_type = self._require_non_empty_string(payload.get("type"), "type")
        if suggestion_type not in ALLOWED_SUGGESTION_TYPES:
            raise SuggestionsValidationError(f"type unsupported: {suggestion_type}")

        severity = self._require_non_empty_string(payload.get("severity"), "severity").upper()
        if severity not in ALLOWED_SEVERITY:
            raise SuggestionsValidationError(f"severity unsupported: {severity}")

        title = self._require_non_empty_string(payload.get("title"), "title")
        detail = self._require_non_empty_string(payload.get("detail"), "detail")
        dismissed_raw = payload.get("dismissed")
        if not isinstance(dismissed_raw, bool):
            raise SuggestionsValidationError("dismissed must be boolean")

        return {
            "id": suggestion_id,
            "created_utc": created_utc,
            "type": suggestion_type,
            "severity": severity,
            "title": title,
            "detail": detail,
            "dismissed": dismissed_raw,
        }

    @staticmethod
    def _require_non_empty_string(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or value.strip() == "":
            raise SuggestionsValidationError(f"{field_name} must be non-empty string")
        return value.strip()

    @staticmethod
    def _created_utc_sortable(created_utc: str) -> str:
        # ISO UTC string lexical ordering matches temporal ordering for fixed format.
        return created_utc

    @staticmethod
    def _sort_key(row: Dict[str, Any]) -> tuple[int, str, str]:
        severity_rank = SEVERITY_RANK.get(str(row.get("severity", "")), 0)
        created_utc = SuggestionsStore._created_utc_sortable(str(row.get("created_utc", "")))
        return severity_rank, created_utc, str(row.get("id", ""))
