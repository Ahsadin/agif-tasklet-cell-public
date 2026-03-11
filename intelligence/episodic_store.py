"""SQLite-backed episodic memory store for AGIF intelligence v2-v5."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DB_PATH = Path("personalization/episodic_memory.db")
DEFAULT_TOP_CORRECTIONS = 5
MAX_TOP_CORRECTIONS = 50
MAX_CORRECTIONS_ROWS = 10_000
MAX_VENDOR_PROFILES_ROWS = 1_000


class EpisodicStoreError(RuntimeError):
    """Base episodic store error."""


class EpisodicValidationError(EpisodicStoreError):
    """Raised for schema-invalid episodic inputs."""


class EpisodicCapacityError(EpisodicStoreError):
    """Raised when a table capacity limit is reached."""


class EpisodicStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self._ensure_parent_dir()
        self._ensure_schema()

    def _ensure_parent_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    wrong_value TEXT NOT NULL,
                    correct_value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    seen_count INTEGER NOT NULL,
                    last_seen_utc TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vendor_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_name TEXT NOT NULL UNIQUE,
                    locale TEXT,
                    currency TEXT,
                    vat_rate_override REAL,
                    updated_utc TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inference_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_utc TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    trigger_event TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    vat_rate_estimate REAL,
                    vat_rate_class TEXT,
                    transformer_confidence REAL,
                    routing_label TEXT
                )
                """
            )
            conn.commit()

    def record_correction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.record_corrections_batch([payload])[0]

    def record_corrections_batch(self, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(payloads, list):
            raise EpisodicValidationError("corrections payload must be array")
        normalized_payloads = [self._normalize_correction(item) for item in payloads]
        if len(normalized_payloads) == 0:
            return []
        with self._connect() as conn:
            correction_count = int(conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0])
            projected = correction_count + len(normalized_payloads)
            if projected > MAX_CORRECTIONS_ROWS:
                raise EpisodicCapacityError(
                    f"corrections row cap exceeded ({MAX_CORRECTIONS_ROWS}); write rejected"
                )
            inserted_rows = []
            for normalized in normalized_payloads:
                cur = conn.execute(
                    """
                    INSERT INTO corrections (
                        vendor_name,
                        field_name,
                        wrong_value,
                        correct_value,
                        confidence,
                        seen_count,
                        last_seen_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        normalized["vendor_name"],
                        normalized["field_name"],
                        normalized["wrong_value"],
                        normalized["correct_value"],
                        normalized["confidence"],
                        normalized["seen_count"],
                        normalized["last_seen_utc"],
                    ),
                )
                result = dict(normalized)
                result["id"] = int(cur.lastrowid)
                inserted_rows.append(result)
            conn.commit()
        return inserted_rows

    def upsert_vendor_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_vendor_profile(payload)
        with self._connect() as conn:
            existing_row = conn.execute(
                "SELECT id FROM vendor_profiles WHERE lower(vendor_name) = lower(?) LIMIT 1",
                (normalized["vendor_name"],),
            ).fetchone()
            if existing_row is None:
                profile_count = int(conn.execute("SELECT COUNT(*) FROM vendor_profiles").fetchone()[0])
                if profile_count >= MAX_VENDOR_PROFILES_ROWS:
                    raise EpisodicCapacityError(
                        f"vendor_profiles row cap exceeded ({MAX_VENDOR_PROFILES_ROWS}); write rejected"
                    )
                cur = conn.execute(
                    """
                    INSERT INTO vendor_profiles (
                        vendor_name,
                        locale,
                        currency,
                        vat_rate_override,
                        updated_utc
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        normalized["vendor_name"],
                        normalized["locale"],
                        normalized["currency"],
                        normalized["vat_rate_override"],
                        normalized["updated_utc"],
                    ),
                )
                profile_id = int(cur.lastrowid)
            else:
                profile_id = int(existing_row[0])
                conn.execute(
                    """
                    UPDATE vendor_profiles
                    SET vendor_name = ?, locale = ?, currency = ?, vat_rate_override = ?, updated_utc = ?
                    WHERE id = ?
                    """,
                    (
                        normalized["vendor_name"],
                        normalized["locale"],
                        normalized["currency"],
                        normalized["vat_rate_override"],
                        normalized["updated_utc"],
                        profile_id,
                    ),
                )
            conn.commit()
        result = dict(normalized)
        result["id"] = profile_id
        return result

    def get_top_corrections(self, vendor_name: str, n: int = DEFAULT_TOP_CORRECTIONS) -> List[Dict[str, Any]]:
        vendor = self._require_non_empty_string(vendor_name, "vendor_name")
        limit = self._normalize_limit(n)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    vendor_name,
                    field_name,
                    wrong_value,
                    correct_value,
                    confidence,
                    seen_count,
                    last_seen_utc
                FROM corrections
                WHERE lower(vendor_name) = lower(?)
                ORDER BY seen_count DESC, confidence DESC, last_seen_utc DESC, id DESC
                LIMIT ?
                """,
                (vendor, limit),
            ).fetchall()
        return [self._correction_row_to_dict(row) for row in rows]

    def get_vendor_profile(self, vendor_name: str) -> Optional[Dict[str, Any]]:
        vendor = self._require_non_empty_string(vendor_name, "vendor_name")
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    vendor_name,
                    locale,
                    currency,
                    vat_rate_override,
                    updated_utc
                FROM vendor_profiles
                WHERE lower(vendor_name) = lower(?)
                LIMIT 1
                """,
                (vendor,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "vendor_name": str(row[1]),
            "locale": row[2] if isinstance(row[2], str) else None,
            "currency": row[3] if isinstance(row[3], str) else None,
            "vat_rate_override": float(row[4]) if isinstance(row[4], (int, float)) else None,
            "updated_utc": str(row[5]),
        }

    def get_counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            correction_count = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
            vendor_profile_count = conn.execute("SELECT COUNT(*) FROM vendor_profiles").fetchone()[0]
        return {
            "corrections": int(correction_count),
            "vendor_profiles": int(vendor_profile_count),
        }

    def record_inference_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_inference_event(payload)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO inference_events (
                    created_utc,
                    doc_id,
                    trigger_event,
                    vendor_name,
                    vat_rate_estimate,
                    vat_rate_class,
                    transformer_confidence,
                    routing_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized["created_utc"],
                    normalized["doc_id"],
                    normalized["trigger_event"],
                    normalized["vendor_name"],
                    normalized["vat_rate_estimate"],
                    normalized["vat_rate_class"],
                    normalized["transformer_confidence"],
                    normalized["routing_label"],
                ),
            )
            conn.commit()
        result = dict(normalized)
        result["id"] = int(cur.lastrowid)
        return result

    def get_vendor_vat_stats(self, vendor_name: str, lookback_days: int = 90) -> Dict[str, Any]:
        vendor = self._require_non_empty_string(vendor_name, "vendor_name")
        lookback = self._normalize_positive_days(lookback_days, "lookback_days")
        now = datetime.now(tz=timezone.utc)
        current_start = now - timedelta(days=30)
        historical_start = current_start - timedelta(days=lookback)

        with self._connect() as conn:
            current_row = conn.execute(
                """
                SELECT AVG(vat_rate_estimate), COUNT(*)
                FROM inference_events
                WHERE lower(vendor_name) = lower(?)
                  AND vat_rate_estimate IS NOT NULL
                  AND created_utc >= ?
                """,
                (vendor, self._dt_to_iso(current_start)),
            ).fetchone()
            historical_row = conn.execute(
                """
                SELECT AVG(vat_rate_estimate), COUNT(*)
                FROM inference_events
                WHERE lower(vendor_name) = lower(?)
                  AND vat_rate_estimate IS NOT NULL
                  AND created_utc >= ?
                  AND created_utc < ?
                """,
                (vendor, self._dt_to_iso(historical_start), self._dt_to_iso(current_start)),
            ).fetchone()

        current_avg = float(current_row[0]) if current_row and isinstance(current_row[0], (int, float)) else None
        historical_avg = (
            float(historical_row[0]) if historical_row and isinstance(historical_row[0], (int, float)) else None
        )
        current_count = int(current_row[1]) if current_row and isinstance(current_row[1], int) else 0
        historical_count = int(historical_row[1]) if historical_row and isinstance(historical_row[1], int) else 0

        return {
            "vendor_name": vendor,
            "current_window_days": 30,
            "historical_window_days": lookback,
            "current_avg_vat_rate": current_avg,
            "historical_avg_vat_rate": historical_avg,
            "current_count": current_count,
            "historical_count": historical_count,
        }

    def get_import_volume_stats(self, current_month: str, prior_months: int = 3) -> Dict[str, Any]:
        month = self._normalize_month(current_month)
        prior = self._normalize_positive_days(prior_months, "prior_months")
        if prior < 1:
            raise EpisodicValidationError("prior_months must be >= 1")
        base_year = int(month[0:4])
        base_month = int(month[5:7])

        months = [month]
        year = base_year
        mon = base_month
        for _ in range(prior):
            mon -= 1
            if mon <= 0:
                year -= 1
                mon = 12
            months.append(f"{year:04d}-{mon:02d}")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT substr(created_utc, 1, 7) AS ym, COUNT(*)
                FROM inference_events
                WHERE substr(created_utc, 1, 7) IN ({})
                GROUP BY ym
                """.format(",".join("?" for _ in months)),
                tuple(months),
            ).fetchall()

        counts_by_month: Dict[str, int] = {value: 0 for value in months}
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 2:
                continue
            ym = str(row[0])
            cnt = int(row[1]) if isinstance(row[1], int) else 0
            if ym in counts_by_month:
                counts_by_month[ym] = cnt

        current_count = counts_by_month[month]
        prior_counts = [counts_by_month[value] for value in months[1:]]
        prior_avg = float(sum(prior_counts)) / float(len(prior_counts)) if len(prior_counts) > 0 else 0.0
        ratio = float(current_count) / prior_avg if prior_avg > 0 else None

        return {
            "current_month": month,
            "current_count": current_count,
            "prior_months": months[1:],
            "prior_counts": prior_counts,
            "prior_average": round(prior_avg, 6),
            "ratio": round(ratio, 6) if isinstance(ratio, float) else None,
        }

    def get_recurring_correction_stats(self, lookback_days: int = 30) -> List[Dict[str, Any]]:
        lookback = self._normalize_positive_days(lookback_days, "lookback_days")
        start = datetime.now(tz=timezone.utc) - timedelta(days=lookback)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    vendor_name,
                    field_name,
                    COUNT(*) AS correction_count,
                    MAX(last_seen_utc) AS last_seen_utc
                FROM corrections
                WHERE last_seen_utc >= ?
                GROUP BY vendor_name, field_name
                ORDER BY correction_count DESC, last_seen_utc DESC
                """,
                (self._dt_to_iso(start),),
            ).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 4:
                continue
            vendor_name = str(row[0])
            field_name = str(row[1])
            correction_count = int(row[2]) if isinstance(row[2], int) else 0
            last_seen_utc = str(row[3]) if isinstance(row[3], str) else ""
            result.append(
                {
                    "vendor_name": vendor_name,
                    "field_name": field_name,
                    "correction_count": correction_count,
                    "last_seen_utc": last_seen_utc,
                    "lookback_days": lookback,
                }
            )
        return result

    def get_inference_event_vendor_names(self, lookback_days: int = 210) -> List[str]:
        lookback = self._normalize_positive_days(lookback_days, "lookback_days")
        start = datetime.now(tz=timezone.utc) - timedelta(days=lookback)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT vendor_name
                FROM inference_events
                WHERE created_utc >= ?
                ORDER BY vendor_name ASC
                """,
                (self._dt_to_iso(start),),
            ).fetchall()
        vendors: List[str] = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) == 0:
                continue
            vendor_name = str(row[0]).strip()
            if vendor_name != "":
                vendors.append(vendor_name)
        return vendors

    def reset(self, scope: str = "all") -> Dict[str, int]:
        normalized_scope = scope.strip().lower() if isinstance(scope, str) else ""
        if normalized_scope not in {"all", "corrections", "vendor_profiles"}:
            raise EpisodicValidationError("scope must be one of: all, corrections, vendor_profiles")

        deleted_corrections = 0
        deleted_vendor_profiles = 0
        with self._connect() as conn:
            if normalized_scope in {"all", "corrections"}:
                deleted_corrections = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
                conn.execute("DELETE FROM corrections")
            if normalized_scope in {"all", "vendor_profiles"}:
                deleted_vendor_profiles = conn.execute("SELECT COUNT(*) FROM vendor_profiles").fetchone()[0]
                conn.execute("DELETE FROM vendor_profiles")
            conn.commit()
        return {
            "deleted_corrections": int(deleted_corrections),
            "deleted_vendor_profiles": int(deleted_vendor_profiles),
        }

    def _normalize_correction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise EpisodicValidationError("correction payload must be object")
        vendor_name = self._require_non_empty_string(payload.get("vendor_name"), "vendor_name")
        field_name = self._require_non_empty_string(payload.get("field_name"), "field_name")
        wrong_value = self._require_non_empty_string(payload.get("wrong_value"), "wrong_value")
        correct_value = self._require_non_empty_string(payload.get("correct_value"), "correct_value")
        confidence_raw = payload.get("confidence", 1.0)
        confidence = self._require_confidence(confidence_raw)
        seen_count_raw = payload.get("seen_count", 1)
        seen_count = self._require_positive_int(seen_count_raw, "seen_count")
        last_seen_utc_raw = payload.get("last_seen_utc")
        if last_seen_utc_raw is None:
            last_seen_utc = self._utc_now_iso()
        elif isinstance(last_seen_utc_raw, str) and last_seen_utc_raw.strip() != "":
            last_seen_utc = last_seen_utc_raw.strip()
        else:
            raise EpisodicValidationError("last_seen_utc must be non-empty string when provided")
        return {
            "vendor_name": vendor_name,
            "field_name": field_name,
            "wrong_value": wrong_value,
            "correct_value": correct_value,
            "confidence": confidence,
            "seen_count": seen_count,
            "last_seen_utc": last_seen_utc,
        }

    def _normalize_vendor_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise EpisodicValidationError("vendor profile payload must be object")
        vendor_name = self._require_non_empty_string(payload.get("vendor_name"), "vendor_name")

        locale_raw = payload.get("locale")
        locale = locale_raw.strip() if isinstance(locale_raw, str) and locale_raw.strip() != "" else None

        currency_raw = payload.get("currency")
        currency = currency_raw.strip() if isinstance(currency_raw, str) and currency_raw.strip() != "" else None

        vat_raw = payload.get("vat_rate_override")
        if vat_raw is None:
            vat_rate_override = None
        elif isinstance(vat_raw, bool) or not isinstance(vat_raw, (int, float)):
            raise EpisodicValidationError("vat_rate_override must be numeric when provided")
        else:
            vat_rate_override = float(vat_raw)

        updated_raw = payload.get("updated_utc")
        if updated_raw is None:
            updated_utc = self._utc_now_iso()
        elif isinstance(updated_raw, str) and updated_raw.strip() != "":
            updated_utc = updated_raw.strip()
        else:
            raise EpisodicValidationError("updated_utc must be non-empty string when provided")

        return {
            "vendor_name": vendor_name,
            "locale": locale,
            "currency": currency,
            "vat_rate_override": vat_rate_override,
            "updated_utc": updated_utc,
        }

    def _normalize_inference_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise EpisodicValidationError("inference event payload must be object")
        created_raw = payload.get("created_utc")
        if created_raw is None:
            created_utc = self._utc_now_iso()
        elif isinstance(created_raw, str) and created_raw.strip() != "":
            created_utc = created_raw.strip()
        else:
            raise EpisodicValidationError("created_utc must be non-empty string when provided")

        doc_id = self._require_non_empty_string(payload.get("doc_id"), "doc_id")
        trigger_event = self._require_non_empty_string(payload.get("trigger_event"), "trigger_event")
        vendor_name = self._require_non_empty_string(payload.get("vendor_name"), "vendor_name")

        vat_rate_estimate_raw = payload.get("vat_rate_estimate")
        vat_rate_estimate = self._optional_float(vat_rate_estimate_raw, "vat_rate_estimate")

        vat_rate_class_raw = payload.get("vat_rate_class")
        if vat_rate_class_raw is None:
            vat_rate_class = None
        elif isinstance(vat_rate_class_raw, str) and vat_rate_class_raw.strip() != "":
            vat_rate_class = vat_rate_class_raw.strip()
        else:
            raise EpisodicValidationError("vat_rate_class must be non-empty string when provided")

        confidence_raw = payload.get("transformer_confidence")
        if confidence_raw is None:
            transformer_confidence = None
        else:
            transformer_confidence = self._require_confidence(confidence_raw)

        routing_label_raw = payload.get("routing_label")
        if routing_label_raw is None:
            routing_label = None
        elif isinstance(routing_label_raw, str) and routing_label_raw.strip() != "":
            routing_label = routing_label_raw.strip()
        else:
            raise EpisodicValidationError("routing_label must be non-empty string when provided")

        return {
            "created_utc": created_utc,
            "doc_id": doc_id,
            "trigger_event": trigger_event,
            "vendor_name": vendor_name,
            "vat_rate_estimate": vat_rate_estimate,
            "vat_rate_class": vat_rate_class,
            "transformer_confidence": transformer_confidence,
            "routing_label": routing_label,
        }

    @staticmethod
    def _require_non_empty_string(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or value.strip() == "":
            raise EpisodicValidationError(f"{field_name} must be non-empty string")
        return value.strip()

    @staticmethod
    def _require_positive_int(value: Any, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise EpisodicValidationError(f"{field_name} must be positive integer")
        return int(value)

    @staticmethod
    def _require_confidence(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EpisodicValidationError("confidence must be numeric")
        numeric = float(value)
        if numeric < 0.0 or numeric > 1.0:
            raise EpisodicValidationError("confidence must be between 0.0 and 1.0")
        return numeric

    @staticmethod
    def _optional_float(value: Any, field_name: str) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EpisodicValidationError(f"{field_name} must be numeric when provided")
        return float(value)

    @staticmethod
    def _normalize_positive_days(value: Any, field_name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise EpisodicValidationError(f"{field_name} must be positive integer")
        return int(value)

    @staticmethod
    def _normalize_month(value: Any) -> str:
        if not isinstance(value, str) or len(value.strip()) != 7:
            raise EpisodicValidationError("current_month must be in YYYY-MM format")
        text = value.strip()
        parts = text.split("-")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise EpisodicValidationError("current_month must be in YYYY-MM format")
        year = int(parts[0])
        month = int(parts[1])
        if year < 2000 or month < 1 or month > 12:
            raise EpisodicValidationError("current_month must be in YYYY-MM format")
        return f"{year:04d}-{month:02d}"

    @staticmethod
    def _dt_to_iso(value: datetime) -> str:
        return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _normalize_limit(n: int) -> int:
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise EpisodicValidationError("n must be positive integer")
        return min(n, MAX_TOP_CORRECTIONS)

    @staticmethod
    def _correction_row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            "id": int(row[0]),
            "vendor_name": str(row[1]),
            "field_name": str(row[2]),
            "wrong_value": str(row[3]),
            "correct_value": str(row[4]),
            "confidence": float(row[5]),
            "seen_count": int(row[6]),
            "last_seen_utc": str(row[7]),
        }
