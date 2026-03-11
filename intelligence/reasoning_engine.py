"""Reasoning config loader and bounded executor for AGIF intelligence v3."""

from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from intelligence.inference.v4_transformer_runner import V4InferenceError, run_v4_vat_inference
except Exception as _v4_import_err:
    V4InferenceError = RuntimeError  # type: ignore[assignment]
    run_v4_vat_inference = None  # type: ignore[assignment]
    V4_IMPORT_WARNING = str(_v4_import_err)
else:
    V4_IMPORT_WARNING = ""

CONFIG_VERSION = "reasoning_steps_v1"
ENGINE_VERSION = "v3"
MAX_STEPS = 10
MAX_STEP_TIMEOUT_MS = 200
GLOBAL_BUDGET_MS = 2000

STATUS_OK = "OK"
STATUS_STEP_TIMEOUT = "STEP_TIMEOUT"
STATUS_STEP_ERROR = "STEP_ERROR"
STATUS_STEP_SKIPPED = "STEP_SKIPPED"

V4_ALLOWED_FALLBACK_CODES = {
    "MODEL_NOT_FOUND",
    "MODEL_LOAD_FAILED",
    "TOKENIZER_FAILED",
    "INFERENCE_TIMEOUT_500MS",
    "INFERENCE_RUNTIME_ERROR",
    "OUTPUT_SCHEMA_INVALID",
}

REQUIRED_STEP_IDS = (
    "extract_numerics",
    "verify_arithmetic",
    "classify_vat_rate",
    "apply_memory_correction",
    "validate_output_schema",
)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "reasoning_steps_v1.json"

DEFAULT_REASONING_CONFIG: Dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "engine_version": ENGINE_VERSION,
    "steps": [
        {
            "id": "extract_numerics",
            "description": "Extract deterministic numeric evidence from OCR text.",
            "timeout_ms": 100,
            "enabled": True,
        },
        {
            "id": "verify_arithmetic",
            "description": "Verify subtotal + tax equals grand total within tolerance.",
            "timeout_ms": 50,
            "enabled": True,
        },
        {
            "id": "classify_vat_rate",
            "description": "Classify VAT rate by deterministic heuristic bands.",
            "timeout_ms": 100,
            "enabled": True,
        },
        {
            "id": "apply_memory_correction",
            "description": "Apply bounded corrections from read-only memory context.",
            "timeout_ms": 50,
            "enabled": True,
        },
        {
            "id": "validate_output_schema",
            "description": "Validate extractor output contract without crashing pipeline.",
            "timeout_ms": 50,
            "enabled": True,
        },
    ],
}


class ReasoningConfigError(ValueError):
    """Raised when reasoning config is invalid."""


@dataclass
class StepResult:
    output: Dict[str, Any]
    note: str
    step_metrics: Dict[str, Any]


OutputValidator = Callable[[Dict[str, Any]], Optional[str]]


def get_default_reasoning_config() -> Dict[str, Any]:
    return deepcopy(DEFAULT_REASONING_CONFIG)


def load_reasoning_config(config_path: Optional[Path] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Load reasoning config and fail-closed to default when missing or invalid."""

    warnings: List[str] = []
    target_path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH

    if not target_path.exists() or not target_path.is_file():
        warnings.append(f"reasoning_config_fallback:missing_or_not_file:{target_path}")
        return get_default_reasoning_config(), warnings

    try:
        raw_value = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception as err:
        warnings.append(f"reasoning_config_fallback:read_or_parse_failed:{err}")
        return get_default_reasoning_config(), warnings

    try:
        validated = validate_reasoning_config(raw_value)
    except ReasoningConfigError as err:
        warnings.append(f"reasoning_config_fallback:validation_failed:{err}")
        return get_default_reasoning_config(), warnings

    return validated, warnings


def validate_reasoning_config(raw_config: Any) -> Dict[str, Any]:
    if not isinstance(raw_config, dict):
        raise ReasoningConfigError("reasoning config must be object")

    config_version = raw_config.get("config_version")
    if config_version != CONFIG_VERSION:
        raise ReasoningConfigError(f"config_version must be {CONFIG_VERSION}")

    engine_version = raw_config.get("engine_version")
    if engine_version != ENGINE_VERSION:
        raise ReasoningConfigError(f"engine_version must be {ENGINE_VERSION}")

    steps = raw_config.get("steps")
    if not isinstance(steps, list):
        raise ReasoningConfigError("steps must be array")

    if len(steps) == 0:
        raise ReasoningConfigError("steps must not be empty")
    if len(steps) > MAX_STEPS:
        raise ReasoningConfigError(f"steps must be <= {MAX_STEPS}")

    normalized_steps: List[Dict[str, Any]] = []
    seen_ids = set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ReasoningConfigError(f"steps[{index}] must be object")

        step_id = _require_non_empty_string(step.get("id"), f"steps[{index}].id")
        if step_id in seen_ids:
            raise ReasoningConfigError(f"duplicate step id: {step_id}")
        seen_ids.add(step_id)

        description = _require_non_empty_string(step.get("description"), f"steps[{index}].description")

        timeout_ms = step.get("timeout_ms")
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int):
            raise ReasoningConfigError(f"steps[{index}].timeout_ms must be integer")
        if timeout_ms < 1 or timeout_ms > MAX_STEP_TIMEOUT_MS:
            raise ReasoningConfigError(
                f"steps[{index}].timeout_ms must be in range 1..{MAX_STEP_TIMEOUT_MS}"
            )

        enabled_raw = step.get("enabled", True)
        if not isinstance(enabled_raw, bool):
            raise ReasoningConfigError(f"steps[{index}].enabled must be boolean")

        normalized_steps.append(
            {
                "id": step_id,
                "description": description,
                "timeout_ms": int(timeout_ms),
                "enabled": enabled_raw,
            }
        )

    missing_required = [step_id for step_id in REQUIRED_STEP_IDS if step_id not in seen_ids]
    if missing_required:
        joined = ",".join(missing_required)
        raise ReasoningConfigError(f"missing required step ids: {joined}")

    required_set = set(REQUIRED_STEP_IDS)
    unexpected_ids = [step_id for step_id in seen_ids if step_id not in required_set]
    if unexpected_ids:
        joined = ",".join(sorted(unexpected_ids))
        raise ReasoningConfigError(f"unexpected step ids: {joined}")

    return {
        "config_version": CONFIG_VERSION,
        "engine_version": ENGINE_VERSION,
        "steps": normalized_steps,
    }


def execute_reasoning(
    output_payload: Dict[str, Any],
    run_input: Optional[Dict[str, Any]] = None,
    config_path: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
    output_validator: Optional[OutputValidator] = None,
) -> Dict[str, Any]:
    """Execute configured steps in order with bounded fail-closed behavior."""

    config_source = "default_fallback"
    config_warnings: List[str] = []

    if config is not None:
        try:
            reasoning_config = validate_reasoning_config(config)
            config_source = "inline_config"
        except ReasoningConfigError as err:
            reasoning_config = get_default_reasoning_config()
            config_warnings.append(f"reasoning_config_fallback:inline_validation_failed:{err}")
            config_source = "default_fallback"
    else:
        reasoning_config, config_warnings = load_reasoning_config(config_path=config_path)
        config_source = "file_config" if len(config_warnings) == 0 else "default_fallback"

    current_output = _normalize_output_payload(output_payload)
    reasoning_trace: List[Dict[str, Any]] = []
    steps = reasoning_config.get("steps", [])
    budget_used_ms = 0

    for step_index, step in enumerate(steps):
        step_id = str(step.get("id", "unknown_step"))
        timeout_ms = int(step.get("timeout_ms", MAX_STEP_TIMEOUT_MS))
        enabled = bool(step.get("enabled", True))

        if budget_used_ms >= GLOBAL_BUDGET_MS:
            reasoning_trace.append(
                _build_trace_item(
                    step_id=step_id,
                    status=STATUS_STEP_SKIPPED,
                    duration_ms=0,
                    note=f"global budget reached ({GLOBAL_BUDGET_MS}ms)",
                    step_metrics={"transformer_confidence": None},
                )
            )
            continue

        if not enabled:
            reasoning_trace.append(
                _build_trace_item(
                    step_id=step_id,
                    status=STATUS_STEP_SKIPPED,
                    duration_ms=0,
                    note="step disabled",
                    step_metrics={"transformer_confidence": None},
                )
            )
            continue

        override = _resolve_step_override(run_input, step_id)
        started_at = time.monotonic()

        try:
            _apply_step_override_pre_run(override)
            step_result = _execute_step(
                step_id=step_id,
                current_output=current_output,
                run_input=run_input,
                output_validator=output_validator,
            )
            status = STATUS_OK
            note = step_result.note
            candidate_output = step_result.output
            step_metrics = step_result.step_metrics
        except Exception as err:
            elapsed_ms_actual = max(0, int((time.monotonic() - started_at) * 1000))
            duration_ms = _resolve_duration_ms(override, elapsed_ms_actual)
            budget_used_ms += duration_ms
            note = f"step error: {err}"
            if step_index == 0 and len(config_warnings) > 0:
                note = f"{note} | {config_warnings[0]}"
            reasoning_trace.append(
                _build_trace_item(
                    step_id=step_id,
                    status=STATUS_STEP_ERROR,
                    duration_ms=duration_ms,
                    note=note,
                    step_metrics={"transformer_confidence": None},
                )
            )
            continue

        elapsed_ms_actual = max(0, int((time.monotonic() - started_at) * 1000))
        duration_ms = _resolve_duration_ms(override, elapsed_ms_actual)
        budget_used_ms += duration_ms

        if duration_ms > timeout_ms:
            status = STATUS_STEP_TIMEOUT
            note = f"step exceeded timeout ({duration_ms}ms > {timeout_ms}ms)"
            step_metrics = {"transformer_confidence": None}
            candidate_output = current_output

        if step_index == 0 and len(config_warnings) > 0:
            if note.strip() == "":
                note = config_warnings[0]
            else:
                note = f"{note} | {config_warnings[0]}"

        current_output = _normalize_output_payload(candidate_output)
        reasoning_trace.append(
            _build_trace_item(
                step_id=step_id,
                status=status,
                duration_ms=duration_ms,
                note=note,
                step_metrics=step_metrics,
            )
        )

    reasoning_summary = _build_reasoning_summary(
        reasoning_trace=reasoning_trace,
        budget_used_ms=budget_used_ms,
        config_source=config_source,
        config_warnings=config_warnings,
    )

    return {
        "final_output": current_output,
        "reasoning_trace": reasoning_trace,
        "reasoning_summary": reasoning_summary,
    }


def _execute_step(
    step_id: str,
    current_output: Dict[str, Any],
    run_input: Optional[Dict[str, Any]],
    output_validator: Optional[OutputValidator],
) -> StepResult:
    if step_id == "extract_numerics":
        return _step_extract_numerics(current_output, run_input)
    if step_id == "verify_arithmetic":
        return _step_verify_arithmetic(current_output, run_input)
    if step_id == "classify_vat_rate":
        return _step_classify_vat_rate(current_output, run_input)
    if step_id == "apply_memory_correction":
        return _step_apply_memory_correction(current_output, run_input)
    if step_id == "validate_output_schema":
        return _step_validate_output_schema(current_output, output_validator)
    raise RuntimeError(f"unsupported reasoning step: {step_id}")


def _step_extract_numerics(current_output: Dict[str, Any], _run_input: Optional[Dict[str, Any]]) -> StepResult:
    next_output = deepcopy(current_output)
    ocr_text = str(next_output.get("ocr_text", ""))
    values = _extract_numeric_values(ocr_text)

    evidence = next_output.get("reasoning_evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    evidence["numerics"] = {
        "count": len(values),
        "values": values[:20],
    }
    next_output["reasoning_evidence"] = evidence

    return StepResult(
        output=next_output,
        note=f"numeric evidence extracted ({len(values)} values)",
        step_metrics={
            "numeric_values_count": len(values),
            "transformer_confidence": None,
        },
    )


def _step_verify_arithmetic(current_output: Dict[str, Any], _run_input: Optional[Dict[str, Any]]) -> StepResult:
    next_output = deepcopy(current_output)
    extracted_fields = next_output.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}
        next_output["extracted_fields"] = extracted_fields

    subtotal = _coerce_number(extracted_fields.get("subtotal"))
    tax_total = _coerce_number(extracted_fields.get("tax_total"))
    grand_total = _coerce_number(extracted_fields.get("grand_total"))
    if subtotal is None or tax_total is None or grand_total is None:
        return StepResult(
            output=next_output,
            note="arithmetic verification skipped: missing numeric totals",
            step_metrics={
                "arithmetic_checked": False,
                "arithmetic_match": False,
                "transformer_confidence": None,
            },
        )

    expected_grand_total = round(subtotal + tax_total, 2)
    observed_grand_total = round(grand_total, 2)
    mismatch = abs(expected_grand_total - observed_grand_total) > 0.01

    warnings = _ensure_warning_list(next_output)
    if mismatch:
        _append_warning_once(warnings, "reasoning_arithmetic_mismatch")
        note = (
            f"arithmetic mismatch: expected grand_total {expected_grand_total:.2f}, "
            f"observed {observed_grand_total:.2f}"
        )
    else:
        note = "arithmetic verified"

    return StepResult(
        output=next_output,
        note=note,
        step_metrics={
            "arithmetic_checked": True,
            "arithmetic_match": not mismatch,
            "transformer_confidence": None,
        },
    )


def _step_classify_vat_rate(current_output: Dict[str, Any], run_input: Optional[Dict[str, Any]]) -> StepResult:
    next_output = deepcopy(current_output)
    extracted_fields = next_output.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}
        next_output["extracted_fields"] = extracted_fields

    subtotal = _coerce_number(extracted_fields.get("subtotal"))
    tax_total = _coerce_number(extracted_fields.get("tax_total"))
    if subtotal is None or tax_total is None or subtotal <= 0:
        extracted_fields["vat_rate_estimate"] = 0.0
        extracted_fields["vat_rate_class"] = "unknown"
        fallback_code = "OUTPUT_SCHEMA_INVALID"
        _append_v4_fallback_warning(next_output, fallback_code)
        return StepResult(
            output=next_output,
            note=f"V4_FALLBACK:{fallback_code} | vat classification skipped: invalid subtotal/tax_total",
            step_metrics={
                "vat_rate_estimate": 0.0,
                "transformer_confidence": 0.0,
                "transformer_backend": "v3_heuristic_fallback",
                "transformer_model_version": "v4",
                "fallback_code": fallback_code,
            },
        )

    vat_rate = float(tax_total) / float(subtotal)
    vat_rate_rounded = round(vat_rate, 4)
    fallback_code: Optional[str] = None
    transformer_backend = "onnx_cpu_int8"
    transformer_model_version = "v4"
    note = ""
    try:
        if run_v4_vat_inference is None:
            raise RuntimeError(f"v4 transformer runner unavailable: {V4_IMPORT_WARNING}")
        model_paths = _resolve_v4_model_paths(run_input)
        inference_result = run_v4_vat_inference(
            ocr_text=str(next_output.get("ocr_text", "")),
            subtotal=float(subtotal),
            tax_total=float(tax_total),
            onnx_path=model_paths.get("onnx_path"),
            metadata_path=model_paths.get("metadata_path"),
            timeout_ms=model_paths.get("timeout_ms", 500),
            simulate_delay_ms=model_paths.get("simulate_delay_ms", 0),
            force_error_code=model_paths.get("force_error_code"),
        )
        vat_class = str(inference_result.get("vat_rate_class", "")).strip()
        if vat_class == "":
            raise V4InferenceError("OUTPUT_SCHEMA_INVALID", "empty vat_rate_class from v4 inference")
        transformer_confidence = inference_result.get("transformer_confidence")
        if isinstance(transformer_confidence, bool) or not isinstance(transformer_confidence, (int, float)):
            raise V4InferenceError("OUTPUT_SCHEMA_INVALID", "invalid transformer_confidence type")
        transformer_backend = str(inference_result.get("transformer_backend", "onnx_cpu_int8"))
        transformer_model_version = str(inference_result.get("transformer_model_version", "v4"))
        fallback_code = inference_result.get("fallback_code")
        note = f"vat rate classified as {vat_class} ({vat_rate_rounded:.4f})"
    except Exception as err:
        fallback_code = _resolve_v4_fallback_code(err)
        vat_class = _classify_vat_rate(vat_rate_rounded)
        transformer_backend = "v3_heuristic_fallback"
        transformer_confidence = _heuristic_transformer_confidence(vat_rate_rounded, vat_class)
        _append_v4_fallback_warning(next_output, fallback_code)
        note = (
            f"V4_FALLBACK:{fallback_code} | "
            f"vat rate classified via v3 heuristic fallback as {vat_class} ({vat_rate_rounded:.4f})"
        )

    extracted_fields["vat_rate_estimate"] = vat_rate_rounded
    extracted_fields["vat_rate_class"] = vat_class

    return StepResult(
        output=next_output,
        note=note,
        step_metrics={
            "vat_rate_estimate": vat_rate_rounded,
            "transformer_confidence": round(float(transformer_confidence), 4),
            "transformer_backend": transformer_backend,
            "transformer_model_version": transformer_model_version,
            "fallback_code": fallback_code,
        },
    )


def _step_apply_memory_correction(current_output: Dict[str, Any], run_input: Optional[Dict[str, Any]]) -> StepResult:
    next_output = deepcopy(current_output)
    extracted_fields = next_output.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}
        next_output["extracted_fields"] = extracted_fields

    memory_context = {}
    if isinstance(run_input, dict):
        context_raw = run_input.get("memory_context")
        if isinstance(context_raw, dict):
            memory_context = context_raw

    top_corrections = memory_context.get("top_corrections")
    if not isinstance(top_corrections, list):
        return StepResult(
            output=next_output,
            note="memory correction skipped: memory context unavailable",
            step_metrics={"memory_hits": 0, "transformer_confidence": None},
        )

    memory_hits = 0
    for correction in top_corrections[:5]:
        if not isinstance(correction, dict):
            continue
        field_name = correction.get("field_name")
        if not isinstance(field_name, str) or field_name not in extracted_fields:
            continue
        if "correct_value" not in correction:
            continue
        before_value = extracted_fields.get(field_name)
        corrected_value = _coerce_like(before_value, correction.get("correct_value"))
        if corrected_value == before_value:
            continue
        extracted_fields[field_name] = corrected_value
        memory_hits += 1

    warnings = _ensure_warning_list(next_output)
    if memory_hits > 0:
        _append_warning_once(warnings, f"memory_corrections_applied:{memory_hits}")
        note = f"memory corrections applied ({memory_hits})"
    else:
        note = "memory corrections not applied"

    return StepResult(
        output=next_output,
        note=note,
        step_metrics={"memory_hits": memory_hits, "transformer_confidence": None},
    )


def _step_validate_output_schema(
    current_output: Dict[str, Any],
    output_validator: Optional[OutputValidator],
) -> StepResult:
    next_output = deepcopy(current_output)
    schema_valid = True
    if output_validator is not None:
        validation_error = output_validator(next_output)
    else:
        validation_error = _default_output_validator(next_output)
    if validation_error is None:
        note = "schema valid"
    else:
        schema_valid = False
        note = f"schema invalid: {validation_error}"
        warnings = _ensure_warning_list(next_output)
        _append_warning_once(warnings, "reasoning_schema_invalid")

    return StepResult(
        output=next_output,
        note=note,
        step_metrics={"schema_valid": schema_valid, "transformer_confidence": None},
    )


def _resolve_v4_model_paths(run_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {
        "onnx_path": None,
        "metadata_path": None,
        "timeout_ms": 500,
        "simulate_delay_ms": 0,
        "force_error_code": None,
    }
    if not isinstance(run_input, dict):
        return defaults

    v4_runtime = run_input.get("v4_transformer")
    if isinstance(v4_runtime, dict):
        onnx_path = v4_runtime.get("onnx_path")
        metadata_path = v4_runtime.get("metadata_path")
        timeout_ms = v4_runtime.get("timeout_ms")
        force_error_code = v4_runtime.get("force_error_code")
        if isinstance(onnx_path, str) and onnx_path.strip() != "":
            defaults["onnx_path"] = onnx_path
        if isinstance(metadata_path, str) and metadata_path.strip() != "":
            defaults["metadata_path"] = metadata_path
        if isinstance(timeout_ms, int) and not isinstance(timeout_ms, bool) and timeout_ms > 0:
            defaults["timeout_ms"] = timeout_ms
        if isinstance(force_error_code, str) and force_error_code.strip() != "":
            defaults["force_error_code"] = force_error_code.strip()

    overrides = run_input.get("reasoning_test_overrides")
    if isinstance(overrides, dict):
        classify_override = overrides.get("classify_vat_rate")
        if isinstance(classify_override, dict):
            simulate_delay = classify_override.get("v4_simulate_delay_ms")
            if isinstance(simulate_delay, int) and not isinstance(simulate_delay, bool) and simulate_delay >= 0:
                defaults["simulate_delay_ms"] = simulate_delay

    return defaults


def _extract_numeric_values(ocr_text: str) -> List[float]:
    token_pattern = r"[-+]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})|[-+]?\d+(?:[.,]\d{1,2})"
    values: List[float] = []
    for token in re.findall(token_pattern, ocr_text):
        parsed = _parse_amount_token(token)
        if parsed is not None:
            values.append(parsed)
    return values


def _parse_amount_token(token: str) -> Optional[float]:
    value = token.strip()
    if value == "":
        return None
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value and "." not in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        value = value.replace(",", "")
    try:
        return round(float(value), 4)
    except Exception:
        return None


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
        except ValueError:
            return None
    return None


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


def _resolve_v4_fallback_code(err: Exception) -> str:
    raw_code = getattr(err, "code", None)
    if isinstance(raw_code, str) and raw_code.strip() != "":
        candidate = raw_code.strip()
        if candidate in V4_ALLOWED_FALLBACK_CODES:
            return candidate
        return "INFERENCE_RUNTIME_ERROR"
    if run_v4_vat_inference is None:
        return "MODEL_LOAD_FAILED"
    return "INFERENCE_RUNTIME_ERROR"


def _heuristic_transformer_confidence(vat_rate: float, vat_class: str) -> float:
    class_center = {
        "zero_or_exempt": 0.0,
        "reduced_low": 0.055,
        "reduced_high": 0.12,
        "standard": 0.19,
        "high_or_outlier": 0.27,
        "unknown": 0.0,
    }.get(vat_class, 0.15)
    distance = abs(float(vat_rate) - float(class_center))
    confidence = 0.58 - min(distance * 0.7, 0.16)
    confidence = max(0.50, min(0.89, confidence))
    return round(confidence, 4)


def _append_v4_fallback_warning(output_payload: Dict[str, Any], fallback_code: str) -> None:
    warnings = _ensure_warning_list(output_payload)
    _append_warning_once(warnings, f"V4_FALLBACK:{fallback_code}")


def _coerce_like(current_value: Any, incoming_value: Any) -> Any:
    if isinstance(current_value, bool):
        if isinstance(incoming_value, bool):
            return incoming_value
        incoming_text = str(incoming_value).strip().lower()
        if incoming_text in {"true", "1", "yes"}:
            return True
        if incoming_text in {"false", "0", "no"}:
            return False
        return current_value
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        try:
            return int(float(incoming_value))
        except Exception:
            return current_value
    if isinstance(current_value, float):
        try:
            return float(incoming_value)
        except Exception:
            return current_value
    return str(incoming_value)


def _ensure_warning_list(output_payload: Dict[str, Any]) -> List[str]:
    warnings = output_payload.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
        output_payload["warnings"] = warnings
    normalized = [str(item) for item in warnings]
    output_payload["warnings"] = normalized
    return normalized


def _append_warning_once(warnings: List[str], value: str) -> None:
    if value not in warnings:
        warnings.append(value)


def _default_output_validator(output_value: Dict[str, Any]) -> Optional[str]:
    if not isinstance(output_value, dict):
        return "output must be object"

    for key in ("doc_id", "source_type", "import_event", "ocr_text", "locale", "currency_hint", "routing_label"):
        value = output_value.get(key)
        if not isinstance(value, str) or value.strip() == "":
            return f"output.{key} must be non-empty string"

    confidence = output_value.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return "output.confidence must be number"

    account_context = output_value.get("account_context")
    if not isinstance(account_context, dict):
        return "output.account_context must be object"
    for key in ("ledger_profile", "cost_center"):
        value = account_context.get(key)
        if not isinstance(value, str) or value.strip() == "":
            return f"output.account_context.{key} must be non-empty string"
    vendor_hint = account_context.get("vendor_hint", "")
    if not isinstance(vendor_hint, str):
        return "output.account_context.vendor_hint must be string when provided"

    extracted_fields = output_value.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        return "output.extracted_fields must be object"
    for key in ("vendor_name", "invoice_date", "due_date", "currency"):
        value = extracted_fields.get(key)
        if not isinstance(value, str) or value.strip() == "":
            return f"output.extracted_fields.{key} must be non-empty string"
    invoice_number = extracted_fields.get("invoice_number", "")
    if not isinstance(invoice_number, str):
        return "output.extracted_fields.invoice_number must be string"
    for key in ("subtotal", "tax_total", "grand_total"):
        value = extracted_fields.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"output.extracted_fields.{key} must be number"

    warnings = output_value.get("warnings")
    if not isinstance(warnings, list):
        return "output.warnings must be array"
    for index, warning in enumerate(warnings):
        if not isinstance(warning, str):
            return f"output.warnings[{index}] must be string"

    ranking = output_value.get("ranking")
    if not isinstance(ranking, list):
        return "output.ranking must be array"
    for index, row in enumerate(ranking):
        if not isinstance(row, dict):
            return f"output.ranking[{index}] must be object"
        candidate = row.get("candidate")
        if not isinstance(candidate, str) or candidate.strip() == "":
            return f"output.ranking[{index}].candidate must be non-empty string"
        score = row.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return f"output.ranking[{index}].score must be number"
        reason = row.get("reason", "")
        if not isinstance(reason, str):
            return f"output.ranking[{index}].reason must be string when provided"

    return None


def _resolve_step_override(run_input: Optional[Dict[str, Any]], step_id: str) -> Dict[str, Any]:
    default = {
        "raise_error": False,
        "sleep_ms": 0,
        "force_duration_ms": None,
    }
    if not isinstance(run_input, dict):
        return default

    overrides = run_input.get("reasoning_test_overrides")
    if not isinstance(overrides, dict):
        return default

    step_override = overrides.get(step_id)
    if not isinstance(step_override, dict):
        return default

    raise_error = step_override.get("raise_error", False)
    if isinstance(raise_error, bool):
        default["raise_error"] = raise_error

    sleep_ms = step_override.get("sleep_ms")
    if isinstance(sleep_ms, int) and not isinstance(sleep_ms, bool) and sleep_ms > 0:
        default["sleep_ms"] = sleep_ms

    force_duration_ms = step_override.get("force_duration_ms")
    if isinstance(force_duration_ms, int) and not isinstance(force_duration_ms, bool) and force_duration_ms >= 0:
        default["force_duration_ms"] = force_duration_ms

    return default


def _apply_step_override_pre_run(step_override: Dict[str, Any]) -> None:
    if bool(step_override.get("raise_error", False)):
        raise RuntimeError("forced step error")
    sleep_ms = step_override.get("sleep_ms", 0)
    if isinstance(sleep_ms, int) and sleep_ms > 0:
        time.sleep(float(sleep_ms) / 1000.0)


def _resolve_duration_ms(step_override: Dict[str, Any], elapsed_ms_actual: int) -> int:
    forced = step_override.get("force_duration_ms")
    if isinstance(forced, int) and not isinstance(forced, bool) and forced >= 0:
        return forced
    return max(0, int(elapsed_ms_actual))


def _build_trace_item(
    step_id: str,
    status: str,
    duration_ms: int,
    note: str,
    step_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_metrics = _normalize_step_metrics(step_metrics)
    return {
        "step_id": str(step_id),
        "status": str(status),
        "duration_ms": max(0, int(duration_ms)),
        "note": str(note),
        "step_metrics": normalized_metrics,
    }


def _normalize_step_metrics(step_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {"transformer_confidence": None}
    if isinstance(step_metrics, dict):
        for key, value in step_metrics.items():
            normalized[str(key)] = value
    transformer_confidence = normalized.get("transformer_confidence")
    if not isinstance(transformer_confidence, (int, float)) and transformer_confidence is not None:
        normalized["transformer_confidence"] = None
    fallback_code = normalized.get("fallback_code")
    if fallback_code is not None:
        if not isinstance(fallback_code, str) or fallback_code not in V4_ALLOWED_FALLBACK_CODES:
            normalized["fallback_code"] = None
    return normalized


def _build_reasoning_summary(
    reasoning_trace: List[Dict[str, Any]],
    budget_used_ms: int,
    config_source: str,
    config_warnings: List[str],
) -> Dict[str, Any]:
    counts = {
        STATUS_OK: 0,
        STATUS_STEP_TIMEOUT: 0,
        STATUS_STEP_ERROR: 0,
        STATUS_STEP_SKIPPED: 0,
    }
    for item in reasoning_trace:
        status = str(item.get("status", ""))
        if status in counts:
            counts[status] += 1

    return {
        "engine_version": ENGINE_VERSION,
        "config_version": CONFIG_VERSION,
        "config_source": config_source,
        "global_budget_ms": GLOBAL_BUDGET_MS,
        "budget_used_ms": max(0, int(budget_used_ms)),
        "steps_total": len(reasoning_trace),
        "steps_ok": counts[STATUS_OK],
        "steps_timeout": counts[STATUS_STEP_TIMEOUT],
        "steps_error": counts[STATUS_STEP_ERROR],
        "steps_skipped": counts[STATUS_STEP_SKIPPED],
        "warnings": [str(item) for item in config_warnings],
    }


def _normalize_output_payload(output_payload: Any) -> Dict[str, Any]:
    if isinstance(output_payload, dict):
        return deepcopy(output_payload)
    return {}


def _require_non_empty_string(value: Any, field_path: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ReasoningConfigError(f"{field_path} must be non-empty string")
    return value.strip()
