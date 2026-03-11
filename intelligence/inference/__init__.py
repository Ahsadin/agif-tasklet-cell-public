"""Inference modules for AGIF intelligence upgrades."""

from .v4_transformer_runner import (  # noqa: F401
    ALLOWED_FALLBACK_CODES,
    BACKEND_ONNX_CPU_INT8,
    CPU_PROVIDER,
    DEFAULT_METADATA_PATH,
    DEFAULT_MAX_TOKENS,
    DEFAULT_ONNX_PATH,
    DEFAULT_TIMEOUT_MS,
    FALLBACK_CODE_INFERENCE_RUNTIME_ERROR,
    FALLBACK_CODE_INFERENCE_TIMEOUT_500MS,
    FALLBACK_CODE_MODEL_LOAD_FAILED,
    FALLBACK_CODE_MODEL_NOT_FOUND,
    FALLBACK_CODE_OUTPUT_SCHEMA_INVALID,
    FALLBACK_CODE_TOKENIZER_FAILED,
    V4InferenceError,
    bootstrap_onnx_runtime_cpu,
    deterministic_tokenize_text,
    run_v4_vat_inference,
)
