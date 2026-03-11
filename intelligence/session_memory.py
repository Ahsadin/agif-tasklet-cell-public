"""In-memory session memory for short-lived context enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


DEFAULT_CONTEXT_WINDOW = 10
DEFAULT_MAX_ENTRIES = 50


@dataclass(frozen=True)
class SessionEvent:
    timestamp: str
    event_type: str
    doc_id: str
    vendor_hint: str
    extracted_fields: Dict[str, Any]
    corrections_applied: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "doc_id": self.doc_id,
            "vendor_hint": self.vendor_hint,
            "extracted_fields": dict(self.extracted_fields),
            "corrections_applied": [dict(item) for item in self.corrections_applied],
        }


class SessionMemory:
    """Stores recent session events in process memory only."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES):
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = int(max_entries)
        self._events: List[SessionEvent] = []

    def add_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_event(event)
        self._events.append(normalized)
        if len(self._events) > self._max_entries:
            self._events = self._events[-self._max_entries :]
        return normalized.as_dict()

    def get_context_window(self, n: int = DEFAULT_CONTEXT_WINDOW) -> List[Dict[str, Any]]:
        if n <= 0:
            return []
        return [entry.as_dict() for entry in self._events[-int(n) :]]

    def clear(self) -> None:
        self._events = []

    def count(self) -> int:
        return len(self._events)

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def _normalize_event(self, event: Dict[str, Any]) -> SessionEvent:
        if not isinstance(event, dict):
            raise ValueError("session event must be object")

        timestamp = event.get("timestamp")
        if not isinstance(timestamp, str) or timestamp.strip() == "":
            timestamp = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        event_type = event.get("event_type")
        if not isinstance(event_type, str) or event_type.strip() == "":
            raise ValueError("session event event_type must be non-empty string")

        doc_id = event.get("doc_id")
        if not isinstance(doc_id, str) or doc_id.strip() == "":
            raise ValueError("session event doc_id must be non-empty string")

        vendor_hint = event.get("vendor_hint", "")
        if not isinstance(vendor_hint, str):
            vendor_hint = ""

        extracted_fields = event.get("extracted_fields", {})
        if not isinstance(extracted_fields, dict):
            raise ValueError("session event extracted_fields must be object")

        corrections_applied = event.get("corrections_applied", [])
        if not isinstance(corrections_applied, list):
            raise ValueError("session event corrections_applied must be array")

        normalized_corrections: List[Dict[str, Any]] = []
        for idx, correction in enumerate(corrections_applied):
            if not isinstance(correction, dict):
                raise ValueError(f"session event corrections_applied[{idx}] must be object")
            normalized_corrections.append(dict(correction))

        return SessionEvent(
            timestamp=timestamp.strip(),
            event_type=event_type.strip(),
            doc_id=doc_id.strip(),
            vendor_hint=vendor_hint.strip(),
            extracted_fields=dict(extracted_fields),
            corrections_applied=normalized_corrections,
        )
