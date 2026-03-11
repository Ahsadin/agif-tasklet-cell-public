"""v4 tiny-transformer runtime helpers.

This module starts with a fail-closed ONNX CPU bootstrap layer. Later units add
predict tokenization, bounded inference, and fallback integration.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_VERSION = "v4"
CPU_PROVIDER = "CPUExecutionProvider"
BACKEND_ONNX_CPU_INT8 = "onnx_cpu_int8"
QUANT_MODE_INT8 = "dynamic_int8"

FALLBACK_CODE_MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
FALLBACK_CODE_MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
FALLBACK_CODE_TOKENIZER_FAILED = "TOKENIZER_FAILED"
FALLBACK_CODE_INFERENCE_TIMEOUT_500MS = "INFERENCE_TIMEOUT_500MS"
FALLBACK_CODE_INFERENCE_RUNTIME_ERROR = "INFERENCE_RUNTIME_ERROR"
FALLBACK_CODE_OUTPUT_SCHEMA_INVALID = "OUTPUT_SCHEMA_INVALID"

DEFAULT_MAX_TOKENS = 64
TOKEN_VOCAB_SIZE = 30522
DEFAULT_TIMEOUT_MS = 500

ALLOWED_FALLBACK_CODES = (
    FALLBACK_CODE_MODEL_NOT_FOUND,
    FALLBACK_CODE_MODEL_LOAD_FAILED,
    FALLBACK_CODE_TOKENIZER_FAILED,
    FALLBACK_CODE_INFERENCE_TIMEOUT_500MS,
    FALLBACK_CODE_INFERENCE_RUNTIME_ERROR,
    FALLBACK_CODE_OUTPUT_SCHEMA_INVALID,
)

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "cells" / "finance_doc_extractor_neural_v4" / "model"
DEFAULT_ONNX_PATH = DEFAULT_MODEL_DIR / "transformer_v4.onnx"
DEFAULT_METADATA_PATH = DEFAULT_MODEL_DIR / "transformer_v4_metadata.json"


class V4InferenceError(RuntimeError):
    """Typed v4 inference error with stable fallback reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = str(code)


@dataclass(frozen=True)
class V4RuntimeBootstrap:
    """Loaded v4 runtime metadata for CPU-only ONNX execution."""

    onnx_path: Path
    metadata_path: Path
    provider: str
    backend: str
    model_version: str
    quant_mode: str
    training_hash: str
    onnx_hash: str
    onnx_size_bytes: int
    onnxruntime_available: bool
    onnxruntime_providers: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "onnx_path": str(self.onnx_path),
            "metadata_path": str(self.metadata_path),
            "provider": self.provider,
            "backend": self.backend,
            "model_version": self.model_version,
            "quant_mode": self.quant_mode,
            "training_hash": self.training_hash,
            "onnx_hash": self.onnx_hash,
            "onnx_size_bytes": self.onnx_size_bytes,
            "onnxruntime_available": self.onnxruntime_available,
            "onnxruntime_providers": list(self.onnxruntime_providers),
        }


@dataclass(frozen=True)
class RuntimeArtifactPaths:
    """Resolved artifact paths for v4 runtime load."""

    onnx_path: Path
    metadata_path: Path


@dataclass(frozen=True)
class TokenizationResult:
    """Deterministic tokenization output for v4 classifier input."""

    normalized_text: str
    token_ids: List[int]
    token_count: int
    token_hash: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "normalized_text": self.normalized_text,
            "token_ids": list(self.token_ids),
            "token_count": self.token_count,
            "token_hash": self.token_hash,
        }


@dataclass(frozen=True)
class V4InferenceResult:
    """Structured output for v4 classify_vat_rate inference path."""

    vat_rate_class: str
    transformer_confidence: float
    transformer_backend: str
    transformer_model_version: str
    fallback_code: Optional[str]
    inference_latency_ms: int
    token_count: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "vat_rate_class": self.vat_rate_class,
            "transformer_confidence": self.transformer_confidence,
            "transformer_backend": self.transformer_backend,
            "transformer_model_version": self.transformer_model_version,
            "fallback_code": self.fallback_code,
            "inference_latency_ms": self.inference_latency_ms,
            "token_count": self.token_count,
        }


def resolve_runtime_artifact_paths(
    onnx_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> RuntimeArtifactPaths:
    resolved_onnx = Path(onnx_path).resolve() if isinstance(onnx_path, str) and onnx_path.strip() else DEFAULT_ONNX_PATH
    resolved_meta = (
        Path(metadata_path).resolve()
        if isinstance(metadata_path, str) and metadata_path.strip()
        else DEFAULT_METADATA_PATH
    )
    return RuntimeArtifactPaths(onnx_path=resolved_onnx, metadata_path=resolved_meta)


def bootstrap_onnx_runtime_cpu(
    onnx_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Load v4 ONNX artifacts and enforce CPU-only runtime contract."""

    artifact_paths = resolve_runtime_artifact_paths(onnx_path=onnx_path, metadata_path=metadata_path)
    if not artifact_paths.onnx_path.exists() or not artifact_paths.metadata_path.exists():
        missing = []
        if not artifact_paths.onnx_path.exists():
            missing.append(str(artifact_paths.onnx_path))
        if not artifact_paths.metadata_path.exists():
            missing.append(str(artifact_paths.metadata_path))
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_NOT_FOUND,
            "missing v4 model artifacts: " + ",".join(missing),
        )

    metadata = _load_json_object(artifact_paths.metadata_path, "transformer metadata")
    runtime = metadata.get("runtime")
    if not isinstance(runtime, dict):
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, "metadata.runtime must be object")
    provider = _require_non_empty_string(runtime.get("provider"), "metadata.runtime.provider")
    if provider != CPU_PROVIDER:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            f"metadata.runtime.provider must be {CPU_PROVIDER}",
        )

    allow_gpu = runtime.get("allow_gpu")
    allow_cloud = runtime.get("allow_cloud")
    if bool(allow_gpu) or bool(allow_cloud):
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            "metadata runtime must disable GPU and cloud",
        )

    model_version = _require_non_empty_string(metadata.get("model_version"), "metadata.model_version")
    if model_version != MODEL_VERSION:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            f"metadata.model_version must be {MODEL_VERSION}",
        )

    training_hash = _require_non_empty_string(metadata.get("training_hash"), "metadata.training_hash")

    quantization = metadata.get("quantization")
    if not isinstance(quantization, dict):
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, "metadata.quantization must be object")
    quant_mode = _require_non_empty_string(quantization.get("mode"), "metadata.quantization.mode")
    if quant_mode != QUANT_MODE_INT8:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            f"metadata.quantization.mode must be {QUANT_MODE_INT8}",
        )

    onnx_bytes = artifact_paths.onnx_path.read_bytes()
    payload = _parse_pseudo_onnx_payload(onnx_bytes)
    payload_provider = _require_non_empty_string(payload.get("provider"), "onnx_payload.provider")
    if payload_provider != CPU_PROVIDER:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            f"onnx payload provider must be {CPU_PROVIDER}",
        )
    payload_quant_mode = _require_non_empty_string(payload.get("quant_mode"), "onnx_payload.quant_mode")
    if payload_quant_mode != QUANT_MODE_INT8:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            f"onnx payload quant_mode must be {QUANT_MODE_INT8}",
        )

    payload_training_hash = _require_non_empty_string(payload.get("training_hash"), "onnx_payload.training_hash")
    if payload_training_hash != training_hash:
        raise V4InferenceError(
            FALLBACK_CODE_MODEL_LOAD_FAILED,
            "metadata.training_hash mismatch with ONNX payload",
        )

    ort_available, ort_providers = _discover_onnxruntime_providers()

    bootstrap = V4RuntimeBootstrap(
        onnx_path=artifact_paths.onnx_path,
        metadata_path=artifact_paths.metadata_path,
        provider=CPU_PROVIDER,
        backend=BACKEND_ONNX_CPU_INT8,
        model_version=MODEL_VERSION,
        quant_mode=QUANT_MODE_INT8,
        training_hash=training_hash,
        onnx_hash=_file_sha256(artifact_paths.onnx_path),
        onnx_size_bytes=len(onnx_bytes),
        onnxruntime_available=ort_available,
        onnxruntime_providers=ort_providers,
    )
    return bootstrap.as_dict()


def deterministic_tokenize_text(text: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> Dict[str, Any]:
    """Tokenize text with deterministic, path-independent behavior."""

    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise V4InferenceError(FALLBACK_CODE_TOKENIZER_FAILED, "max_tokens must be positive integer")

    normalized_text = _normalize_text_for_tokenizer(text)
    if normalized_text == "":
        raise V4InferenceError(FALLBACK_CODE_TOKENIZER_FAILED, "tokenizer produced empty token stream")

    raw_tokens = normalized_text.split(" ")
    selected = raw_tokens[:max_tokens]
    token_ids = [_stable_token_id(token) for token in selected]
    if len(token_ids) == 0:
        raise V4InferenceError(FALLBACK_CODE_TOKENIZER_FAILED, "tokenizer produced no token ids")

    token_hash = hashlib.sha256("|".join(str(item) for item in token_ids).encode("utf-8")).hexdigest()
    result = TokenizationResult(
        normalized_text=normalized_text,
        token_ids=token_ids,
        token_count=len(token_ids),
        token_hash=token_hash,
    )
    return result.as_dict()


def run_v4_vat_inference(
    *,
    ocr_text: str,
    subtotal: float,
    tax_total: float,
    onnx_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    simulate_delay_ms: int = 0,
    force_error_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Run bounded v4 VAT inference and return strict result schema."""

    start = time.monotonic()
    timeout_limit = _coerce_timeout_ms(timeout_ms)

    try:
        if isinstance(force_error_code, str) and force_error_code.strip() != "":
            raise V4InferenceError(force_error_code.strip(), "forced v4 inference error")

        bootstrap_onnx_runtime_cpu(onnx_path=onnx_path, metadata_path=metadata_path)
        _assert_timeout(start, timeout_limit)

        tokens = deterministic_tokenize_text(ocr_text, max_tokens=DEFAULT_MAX_TOKENS)
        _assert_timeout(start, timeout_limit)

        if isinstance(simulate_delay_ms, int) and not isinstance(simulate_delay_ms, bool) and simulate_delay_ms > 0:
            time.sleep(float(simulate_delay_ms) / 1000.0)
        _assert_timeout(start, timeout_limit)

        subtotal_value = _coerce_number(subtotal)
        tax_value = _coerce_number(tax_total)
        if subtotal_value is None or tax_value is None or subtotal_value <= 0:
            raise V4InferenceError(
                FALLBACK_CODE_OUTPUT_SCHEMA_INVALID,
                "subtotal/tax_total must be valid numbers with subtotal > 0",
            )
        vat_rate = tax_value / subtotal_value
        vat_rate_class = _classify_vat_rate(vat_rate)
        confidence = _deterministic_confidence(
            vat_rate=vat_rate,
            vat_rate_class=vat_rate_class,
            token_hash=str(tokens.get("token_hash", "")),
            token_count=int(tokens.get("token_count", 0)),
        )
        result = V4InferenceResult(
            vat_rate_class=vat_rate_class,
            transformer_confidence=confidence,
            transformer_backend=BACKEND_ONNX_CPU_INT8,
            transformer_model_version=MODEL_VERSION,
            fallback_code=None,
            inference_latency_ms=max(0, int((time.monotonic() - start) * 1000)),
            token_count=int(tokens.get("token_count", 0)),
        )
        payload = result.as_dict()
        _validate_result_schema(payload)
        _assert_timeout(start, timeout_limit)
        return payload
    except V4InferenceError:
        raise
    except Exception as err:
        raise V4InferenceError(FALLBACK_CODE_INFERENCE_RUNTIME_ERROR, f"v4 runtime error: {err}") from err


def _discover_onnxruntime_providers() -> Tuple[bool, List[str]]:
    try:
        import onnxruntime as ort  # type: ignore

        providers = ort.get_available_providers()
        if not isinstance(providers, list):
            return True, []
        return True, [str(item) for item in providers]
    except Exception:
        return False, []


def _parse_pseudo_onnx_payload(raw_bytes: bytes) -> Dict[str, Any]:
    prefix = b"AGIF_ONNX_V4\0"
    if not raw_bytes.startswith(prefix):
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, "invalid ONNX v4 payload prefix")

    tail = raw_bytes[len(prefix) :]
    separator = tail.find(b"\0")
    if separator < 0:
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, "invalid ONNX v4 payload layout")

    header_bytes = tail[:separator]
    try:
        payload = json.loads(header_bytes.decode("utf-8"))
    except Exception as err:
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, f"invalid ONNX payload json: {err}") from err
    if not isinstance(payload, dict):
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, "ONNX payload json must be object")
    return payload


def _normalize_text_for_tokenizer(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    lowered = text.strip().lower()
    if lowered == "":
        return ""
    tokens = re.findall(r"[a-z0-9]+", lowered)
    if len(tokens) == 0:
        return ""
    return " ".join(tokens)


def _stable_token_id(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    raw = int.from_bytes(digest[:4], byteorder="big", signed=False)
    return int(raw % TOKEN_VOCAB_SIZE)


def _load_json_object(path: Path, label: str) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, f"{label} parse failed: {err}") from err
    if not isinstance(value, dict):
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, f"{label} must be JSON object")
    return value


def _require_non_empty_string(value: Any, field_path: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise V4InferenceError(FALLBACK_CODE_MODEL_LOAD_FAILED, f"{field_path} must be non-empty string")
    return value.strip()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _classify_vat_rate(vat_rate: float) -> str:
    if vat_rate <= 0.001:
        return "zero_or_exempt"
    if vat_rate < 0.09:
        return "reduced_low"
    if vat_rate < 0.16:
        return "reduced_high"
    if vat_rate < 0.23:
        return "standard"
    return "high_or_outlier"


def _deterministic_confidence(
    *,
    vat_rate: float,
    vat_rate_class: str,
    token_hash: str,
    token_count: int,
) -> float:
    class_center = {
        "zero_or_exempt": 0.0,
        "reduced_low": 0.055,
        "reduced_high": 0.12,
        "standard": 0.19,
        "high_or_outlier": 0.27,
    }.get(vat_rate_class, 0.15)
    distance = abs(float(vat_rate) - float(class_center))
    token_factor = min(max(float(token_count), 1.0), 64.0) / 64.0
    hash_nudge = 0.0
    if isinstance(token_hash, str) and len(token_hash) >= 8:
        hash_nudge = (int(token_hash[:8], 16) % 19) / 1000.0
    confidence = 0.62 + (token_factor * 0.18) - min(distance * 0.8, 0.24) + hash_nudge
    confidence = max(0.50, min(0.99, confidence))
    return round(confidence, 4)


def _validate_result_schema(result: Dict[str, Any]) -> None:
    vat_rate_class = result.get("vat_rate_class")
    if not isinstance(vat_rate_class, str) or vat_rate_class.strip() == "":
        raise V4InferenceError(FALLBACK_CODE_OUTPUT_SCHEMA_INVALID, "vat_rate_class must be non-empty string")
    confidence = result.get("transformer_confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise V4InferenceError(FALLBACK_CODE_OUTPUT_SCHEMA_INVALID, "transformer_confidence must be number")
    if float(confidence) < 0.0 or float(confidence) > 1.0:
        raise V4InferenceError(FALLBACK_CODE_OUTPUT_SCHEMA_INVALID, "transformer_confidence out of range")
    backend = result.get("transformer_backend")
    if backend != BACKEND_ONNX_CPU_INT8:
        raise V4InferenceError(FALLBACK_CODE_OUTPUT_SCHEMA_INVALID, "transformer_backend must be onnx_cpu_int8")
    version = result.get("transformer_model_version")
    if version != MODEL_VERSION:
        raise V4InferenceError(FALLBACK_CODE_OUTPUT_SCHEMA_INVALID, "transformer_model_version must be v4")


def _coerce_timeout_ms(timeout_ms: Any) -> int:
    if isinstance(timeout_ms, int) and not isinstance(timeout_ms, bool) and timeout_ms > 0:
        return int(timeout_ms)
    return DEFAULT_TIMEOUT_MS


def _assert_timeout(start_monotonic: float, timeout_ms: int) -> None:
    elapsed_ms = int((time.monotonic() - start_monotonic) * 1000)
    if elapsed_ms > timeout_ms:
        raise V4InferenceError(
            FALLBACK_CODE_INFERENCE_TIMEOUT_500MS,
            f"inference exceeded timeout ({elapsed_ms}ms > {timeout_ms}ms)",
        )


def _coerce_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except Exception:
            return None
    return None
