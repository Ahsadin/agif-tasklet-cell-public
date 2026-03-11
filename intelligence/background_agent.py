"""Proactive background anomaly agent for v5."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from intelligence.episodic_store import EpisodicStore
from intelligence.suggestions_store import SuggestionsStore

IDLE_WINDOW_SECONDS = 30 * 60
SCAN_INTERVAL_SECONDS = 30 * 60
LOOP_TICK_SECONDS = 5
MIN_CANDIDATE_QUALITY_SCORE = 0.70
MIN_VAT_DEVIATION_RATIO = 0.25
MIN_IMPORT_VOLUME_RATIO = 2.25
MIN_RECURRING_CORRECTION_COUNT = 6


@dataclass
class ScanResult:
    scan_time_utc: str
    scanned: bool
    suggestions_written: int
    warnings: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scan_time_utc": self.scan_time_utc,
            "scanned": self.scanned,
            "suggestions_written": self.suggestions_written,
            "warnings": list(self.warnings),
        }


class BackgroundAgent:
    """Idle-window background scanner producing proactive suggestions."""

    def __init__(
        self,
        *,
        episodic_store: Optional[EpisodicStore] = None,
        suggestions_store: Optional[SuggestionsStore] = None,
        idle_window_seconds: int = IDLE_WINDOW_SECONDS,
        scan_interval_seconds: int = SCAN_INTERVAL_SECONDS,
        loop_tick_seconds: int = LOOP_TICK_SECONDS,
    ):
        self._episodic_store = episodic_store if episodic_store is not None else EpisodicStore()
        self._suggestions_store = suggestions_store if suggestions_store is not None else SuggestionsStore()

        self._idle_window_seconds = max(1, int(idle_window_seconds))
        self._scan_interval_seconds = max(1, int(scan_interval_seconds))
        self._loop_tick_seconds = max(1, int(loop_tick_seconds))

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        now_iso = self._utc_now_iso()
        self._status: Dict[str, Any] = {
            "state": "stopped",
            "started_utc": None,
            "stopped_utc": now_iso,
            "last_scan_utc": None,
            "last_scan_result": None,
            "last_trigger_heartbeat_utc": None,
            "warnings": [],
        }

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(tz=timezone.utc)

    @classmethod
    def _utc_now_iso(cls) -> str:
        return cls._utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def start(self) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="agif-v5-background-agent", daemon=True)
            self._thread.start()
            self._status["state"] = "running"
            self._status["started_utc"] = self._utc_now_iso()
            self._status["stopped_utc"] = None
            return True

    def stop(self, timeout_seconds: float = 3.0) -> bool:
        with self._lock:
            thread = self._thread
            if thread is None:
                self._status["state"] = "stopped"
                self._status["stopped_utc"] = self._utc_now_iso()
                return False
            self._stop_event.set()

        thread.join(timeout=max(0.1, float(timeout_seconds)))

        with self._lock:
            still_running = thread.is_alive()
            if not still_running:
                self._thread = None
                self._status["state"] = "stopped"
                self._status["stopped_utc"] = self._utc_now_iso()
            return not still_running

    def heartbeat_trigger(self, trigger_event: str = "unknown") -> None:
        heartbeat = self._utc_now_iso()
        with self._lock:
            self._status["last_trigger_heartbeat_utc"] = heartbeat
            warnings = self._status.get("warnings")
            if not isinstance(warnings, list):
                warnings = []
            warnings.append(f"heartbeat:{trigger_event}:{heartbeat}")
            self._status["warnings"] = warnings[-20:]

    def status(self) -> Dict[str, Any]:
        with self._lock:
            payload = dict(self._status)
        payload["active_suggestions_count"] = self._safe_active_suggestion_count()
        return payload

    def run_scan_once(self) -> Dict[str, Any]:
        warnings: List[str] = []
        scan_time = self._utc_now_iso()

        try:
            candidates = self._build_candidates(warnings)
            suggestions = self._candidates_to_suggestions(candidates, scan_time_utc=scan_time)
            write_summary = self._suggestions_store.upsert_suggestions(suggestions)
            written_count = int(write_summary.get("inserted", 0)) + int(write_summary.get("updated", 0))
            result = ScanResult(
                scan_time_utc=scan_time,
                scanned=True,
                suggestions_written=written_count,
                warnings=warnings,
            )
        except Exception as err:
            warnings.append(f"V5_FALLBACK:SCAN_RUNTIME_ERROR:{err}")
            result = ScanResult(
                scan_time_utc=scan_time,
                scanned=False,
                suggestions_written=0,
                warnings=warnings,
            )

        with self._lock:
            self._status["last_scan_utc"] = scan_time
            self._status["last_scan_result"] = result.as_dict()
            self._status["warnings"] = warnings[-20:]

        return result.as_dict()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._loop_tick_seconds):
            if not self._is_scan_due():
                continue
            self.run_scan_once()

    def _is_scan_due(self) -> bool:
        now = self._utc_now()
        with self._lock:
            last_trigger = self._parse_iso_utc(self._status.get("last_trigger_heartbeat_utc"))
            last_scan = self._parse_iso_utc(self._status.get("last_scan_utc"))

        if last_trigger is not None:
            idle_for = (now - last_trigger).total_seconds()
            if idle_for < self._idle_window_seconds:
                return False

        if last_scan is None:
            return True

        since_scan = (now - last_scan).total_seconds()
        return since_scan >= self._scan_interval_seconds

    def _build_candidates(self, warnings: List[str]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        try:
            candidates.extend(self._analyze_vat_inconsistency())
        except Exception as err:
            warnings.append(f"V5_FALLBACK:VAT_ANALYZER_FAILED:{err}")

        try:
            candidates.extend(self._analyze_import_volume_spike())
        except Exception as err:
            warnings.append(f"V5_FALLBACK:VOLUME_ANALYZER_FAILED:{err}")

        try:
            candidates.extend(self._analyze_recurring_corrections())
        except Exception as err:
            warnings.append(f"V5_FALLBACK:CORRECTION_ANALYZER_FAILED:{err}")

        return candidates

    def _analyze_vat_inconsistency(self) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        vendors = self._episodic_store.get_inference_event_vendor_names(lookback_days=210)
        for vendor_name in vendors:
            stats = self._episodic_store.get_vendor_vat_stats(vendor_name, lookback_days=180)
            current_avg = stats.get("current_avg_vat_rate")
            historical_avg = stats.get("historical_avg_vat_rate")
            if not isinstance(current_avg, (int, float)) or not isinstance(historical_avg, (int, float)):
                continue
            if abs(float(historical_avg)) < 1e-9:
                continue
            current_count = int(stats.get("current_count", 0))
            historical_count = int(stats.get("historical_count", 0))
            if current_count < 1 or historical_count < 2:
                continue

            deviation = abs(float(current_avg) - float(historical_avg)) / abs(float(historical_avg))
            if deviation < MIN_VAT_DEVIATION_RATIO:
                continue

            quality_score = self._score_vat_candidate(
                deviation=deviation,
                current_count=current_count,
                historical_count=historical_count,
            )
            if quality_score < MIN_CANDIDATE_QUALITY_SCORE:
                continue

            severity = "HIGH" if deviation >= 0.40 else "MEDIUM"
            output.append(
                {
                    "type": "vat_rate_inconsistency",
                    "severity": severity,
                    "title": f"VAT pattern changed for {vendor_name}",
                    "detail": (
                        f"Current avg VAT {float(current_avg):.4f} vs historical avg {float(historical_avg):.4f} "
                        f"(deviation {deviation * 100.0:.2f}%)."
                    ),
                    "fingerprint": f"vat_rate_inconsistency|{vendor_name}|{severity}|{round(deviation, 6)}",
                    "dedupe_key": f"vat_rate_inconsistency|{vendor_name}|{severity}",
                    "quality_score": round(quality_score, 6),
                }
            )
        return output

    def _analyze_import_volume_spike(self) -> List[Dict[str, Any]]:
        current_month = self._utc_now().strftime("%Y-%m")
        stats = self._episodic_store.get_import_volume_stats(current_month=current_month, prior_months=3)
        ratio = stats.get("ratio")
        if not isinstance(ratio, (int, float)):
            return []
        ratio_value = float(ratio)
        if ratio_value < MIN_IMPORT_VOLUME_RATIO:
            return []

        current_count = int(stats.get("current_count", 0))
        prior_avg = float(stats.get("prior_average", 0.0))
        quality_score = self._score_volume_spike_candidate(ratio=ratio_value, current_count=current_count, prior_avg=prior_avg)
        if quality_score < MIN_CANDIDATE_QUALITY_SCORE:
            return []

        severity = "HIGH" if ratio_value >= 3.0 else "MEDIUM"
        return [
            {
                "type": "import_volume_spike",
                "severity": severity,
                "title": "Import volume spike detected",
                "detail": (
                    f"Current month {current_month} imports={current_count}, prior 3-month avg={prior_avg:.2f}, "
                    f"ratio={ratio_value:.2f}x."
                ),
                "fingerprint": f"import_volume_spike|{current_month}|{severity}|{round(ratio_value, 6)}",
                "dedupe_key": f"import_volume_spike|{current_month}|{severity}",
                "quality_score": round(quality_score, 6),
            }
        ]

    def _analyze_recurring_corrections(self) -> List[Dict[str, Any]]:
        output: List[Dict[str, Any]] = []
        rows = self._episodic_store.get_recurring_correction_stats(lookback_days=30)
        for row in rows:
            count = row.get("correction_count")
            if not isinstance(count, int) or count < MIN_RECURRING_CORRECTION_COUNT:
                continue
            quality_score = self._score_recurring_correction_candidate(count)
            if quality_score < MIN_CANDIDATE_QUALITY_SCORE:
                continue
            severity = "HIGH" if count >= 10 else "MEDIUM"
            vendor_name = str(row.get("vendor_name", ""))
            field_name = str(row.get("field_name", ""))
            output.append(
                {
                    "type": "recurring_correction_pattern",
                    "severity": severity,
                    "title": f"Recurring correction pattern: {vendor_name}",
                    "detail": (
                        f"Field '{field_name}' corrected {count} times in the last 30 days for vendor '{vendor_name}'."
                    ),
                    "fingerprint": f"recurring_correction_pattern|{vendor_name}|{field_name}|{severity}|{count}",
                    "dedupe_key": f"recurring_correction_pattern|{vendor_name}|{field_name}|{severity}",
                    "quality_score": round(quality_score, 6),
                }
            )
        return output

    def _candidates_to_suggestions(self, candidates: List[Dict[str, Any]], scan_time_utc: str) -> List[Dict[str, Any]]:
        best_by_bucket: Dict[str, Dict[str, Any]] = {}
        for item in candidates:
            if not isinstance(item, dict):
                continue
            suggestion_type = str(item.get("type", "")).strip()
            severity = str(item.get("severity", "")).strip().upper()
            title = str(item.get("title", "")).strip()
            detail = str(item.get("detail", "")).strip()
            fingerprint = str(item.get("fingerprint", "")).strip()
            if suggestion_type == "" or severity == "" or title == "" or detail == "" or fingerprint == "":
                continue
            quality_score = self._parse_quality_score(item.get("quality_score"), severity)
            if quality_score < MIN_CANDIDATE_QUALITY_SCORE:
                continue

            dedupe_key = self._normalize_dedupe_key(
                item.get("dedupe_key"),
                suggestion_type=suggestion_type,
                severity=severity,
                title=title,
            )
            bucket = dedupe_key.lower()
            candidate = {
                "type": suggestion_type,
                "severity": severity,
                "title": title,
                "detail": detail,
                "fingerprint": fingerprint,
                "dedupe_key": dedupe_key,
                "quality_score": quality_score,
            }
            previous = best_by_bucket.get(bucket)
            if previous is None or self._is_better_candidate(candidate, previous):
                best_by_bucket[bucket] = candidate

        by_id: Dict[str, Dict[str, Any]] = {}
        for candidate in best_by_bucket.values():
            suggestion_id = "sug_" + hashlib.sha256(candidate["dedupe_key"].encode("utf-8")).hexdigest()[:16]
            by_id[suggestion_id] = {
                "id": suggestion_id,
                "created_utc": scan_time_utc,
                "type": candidate["type"],
                "severity": candidate["severity"],
                "title": candidate["title"],
                "detail": candidate["detail"],
                "dismissed": False,
                "quality_score": candidate["quality_score"],
            }

        out = list(by_id.values())
        out.sort(key=self._sort_candidate_key, reverse=True)
        return out

    @staticmethod
    def _sort_candidate_key(item: Dict[str, Any]) -> tuple[int, float, str, str]:
        rank = BackgroundAgent._severity_rank(str(item.get("severity", "")))
        quality_score = BackgroundAgent._parse_quality_score(item.get("quality_score"), str(item.get("severity", "")))
        return rank, quality_score, str(item.get("created_utc", "")), str(item.get("id", ""))

    @staticmethod
    def _severity_rank(value: str) -> int:
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(str(value).strip().upper(), 0)

    @staticmethod
    def _parse_quality_score(raw: Any, severity: str) -> float:
        defaults = {"HIGH": 0.90, "MEDIUM": 0.78, "LOW": 0.65}
        if isinstance(raw, (int, float)):
            return BackgroundAgent._clamp_score(float(raw))
        return defaults.get(str(severity).strip().upper(), 0.0)

    @staticmethod
    def _clamp_score(value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return float(value)

    @staticmethod
    def _normalize_text_token(value: Any) -> str:
        text = str(value).strip().lower()
        return " ".join(text.split())

    def _normalize_dedupe_key(self, raw: Any, *, suggestion_type: str, severity: str, title: str) -> str:
        if isinstance(raw, str) and raw.strip() != "":
            parts = [self._normalize_text_token(part) for part in raw.split("|")]
            cleaned = [part for part in parts if part != ""]
            if cleaned:
                return "|".join(cleaned)
        return "|".join(
            [
                self._normalize_text_token(suggestion_type),
                self._normalize_text_token(severity),
                self._normalize_text_token(title),
            ]
        )

    def _is_better_candidate(self, current: Dict[str, Any], previous: Dict[str, Any]) -> bool:
        current_quality = self._parse_quality_score(current.get("quality_score"), str(current.get("severity", "")))
        previous_quality = self._parse_quality_score(previous.get("quality_score"), str(previous.get("severity", "")))
        if current_quality != previous_quality:
            return current_quality > previous_quality

        current_rank = self._severity_rank(str(current.get("severity", "")))
        previous_rank = self._severity_rank(str(previous.get("severity", "")))
        if current_rank != previous_rank:
            return current_rank > previous_rank

        return str(current.get("fingerprint", "")) < str(previous.get("fingerprint", ""))

    @staticmethod
    def _score_vat_candidate(*, deviation: float, current_count: int, historical_count: int) -> float:
        deviation_factor = BackgroundAgent._clamp_score(deviation / 0.60)
        current_support = BackgroundAgent._clamp_score(float(current_count + 1) / 3.0)
        historical_support = BackgroundAgent._clamp_score(float(historical_count + 1) / 6.0)
        return BackgroundAgent._clamp_score(
            (deviation_factor * 0.65) + (current_support * 0.20) + (historical_support * 0.15)
        )

    @staticmethod
    def _score_volume_spike_candidate(*, ratio: float, current_count: int, prior_avg: float) -> float:
        ratio_factor = BackgroundAgent._clamp_score((ratio - MIN_IMPORT_VOLUME_RATIO) / 1.5)
        current_support = BackgroundAgent._clamp_score(float(current_count) / 8.0)
        baseline_support = BackgroundAgent._clamp_score(float(prior_avg) / 5.0)
        return BackgroundAgent._clamp_score(
            (ratio_factor * 0.50) + (current_support * 0.30) + (baseline_support * 0.20)
        )

    @staticmethod
    def _score_recurring_correction_candidate(count: int) -> float:
        return BackgroundAgent._clamp_score(float(count) / 10.0)

    @staticmethod
    def _parse_iso_utc(value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or value.strip() == "":
            return None
        text = value.strip()
        try:
            if text.endswith("Z"):
                text = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    def _safe_active_suggestion_count(self) -> int:
        try:
            return int(self._suggestions_store.count_active())
        except Exception:
            return 0
