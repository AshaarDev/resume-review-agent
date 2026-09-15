"""Google GenAI integration for validated multimodal resume analysis."""

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from pydantic import ValidationError

from core.config import settings
from core.review_schemas import VisualReviewResult

logger = logging.getLogger(__name__)

_client: Optional[Any] = None


class GeminiServiceError(RuntimeError):
    """A categorized Gemini failure safe to expose through API metadata."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def get_client() -> Any:
    """Get or create the official Google GenAI SDK client."""

    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise GeminiServiceError(
                "GEMINI_NOT_CONFIGURED",
                "Visual review is unavailable because GEMINI_API_KEY is not set.",
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise GeminiServiceError(
                "GEMINI_SDK_UNAVAILABLE",
                "Visual review is unavailable because google-genai is not installed.",
            ) from exc
        _client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=settings.GEMINI_TIMEOUT_SECONDS * 1000
            ),
        )
    return _client


def reset_client() -> None:
    """Reset the cached client, primarily for configuration tests."""

    global _client
    _client = None


def _classify_api_error(exc: Exception, model: str) -> GeminiServiceError:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if (
        "not_found" in message
        or "no longer available" in message
        or ("404" in message and "model" in message)
    ):
        return GeminiServiceError(
            "GEMINI_MODEL_UNAVAILABLE",
            f"The configured Gemini model '{model}' "
            "is not available for this API account.",
        )
    if "unauthorized" in message or "401" in message:
        return GeminiServiceError(
            "GEMINI_AUTHENTICATION_FAILED",
            "The visual review service could not authenticate with Gemini.",
        )
    if "permission_denied" in message or "forbidden" in message or "403" in message:
        return GeminiServiceError(
            "GEMINI_PERMISSION_DENIED",
            "The Gemini API key cannot access the visual review service.",
        )
    if "timeout" in name or "deadline" in name or "timeout" in message:
        return GeminiServiceError(
            "GEMINI_TIMEOUT", "The visual review request timed out."
        )
    if "resourceexhausted" in name or "rate" in message or "429" in message:
        return GeminiServiceError(
            "GEMINI_RATE_LIMITED",
            "The visual review service is temporarily rate limited.",
        )
    if (
        "service_unavailable" in name
        or "unavailable" in message
        or "high demand" in message
        or "503" in message
    ):
        return GeminiServiceError(
            "GEMINI_SERVICE_UNAVAILABLE",
            "The visual review service is temporarily unavailable.",
        )
    return GeminiServiceError(
        "GEMINI_API_ERROR", "The visual review service failed to respond."
    )


_FALLBACK_ERROR_CODES = {
    "GEMINI_API_ERROR",
    "GEMINI_INVALID_RESPONSE",
    "GEMINI_MODEL_UNAVAILABLE",
    "GEMINI_RATE_LIMITED",
    "GEMINI_SERVICE_UNAVAILABLE",
    "GEMINI_TIMEOUT",
}


def _configured_models() -> List[str]:
    """Return the primary and distinct optional fallback model in call order."""

    primary = settings.GEMINI_VISION_MODEL.strip()
    fallback = settings.GEMINI_VISION_FALLBACK_MODEL.strip()
    models = [primary]
    if fallback and fallback != primary:
        models.append(fallback)
    return models


def _parse_response(response: Any) -> VisualReviewResult:
    """Validate one model response against the shared visual-review schema."""

    try:
        if response.parsed is not None:
            return VisualReviewResult.model_validate(response.parsed)
        if not response.text:
            raise ValueError("Gemini returned an empty response")
        return VisualReviewResult.model_validate_json(response.text)
    except (ValidationError, ValueError, TypeError) as exc:
        raise GeminiServiceError(
            "GEMINI_INVALID_RESPONSE",
            "The visual review service returned an invalid structured response.",
        ) from exc


def analyze_images_structured(
    image_paths: List[Path],
    prompt: str,
    layout_context: Optional[dict] = None,
) -> VisualReviewResult:
    """Send local PNG bytes and validate Gemini's structured response."""

    try:
        from google.genai import types
    except ImportError as exc:
        raise GeminiServiceError(
            "GEMINI_SDK_UNAVAILABLE",
            "Visual review is unavailable because google-genai is not installed.",
        ) from exc

    contents: List[Any] = [
        types.Part.from_text(
            text=prompt
            + (
                "\n\nDeterministic layout measurements:\n"
                + json.dumps(layout_context, separators=(",", ":"))
                if layout_context
                else ""
            )
        )
    ]
    for image_path in image_paths:
        contents.append(
            types.Part.from_bytes(data=image_path.read_bytes(), mime_type="image/png")
        )

    models = _configured_models()
    client = get_client()
    last_error: Optional[GeminiServiceError] = None

    for index, model in enumerate(models):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VisualReviewResult,
                ),
            )
            result = _parse_response(response)
            if index:
                logger.info(
                    "Gemini visual review succeeded with fallback model %s",
                    model,
                )
            return result
        except GeminiServiceError as exc:
            current_error = exc
        except Exception as exc:
            current_error = _classify_api_error(exc, model)

        has_fallback = index + 1 < len(models)
        if has_fallback and current_error.code in _FALLBACK_ERROR_CODES:
            logger.warning(
                "Gemini visual model %s failed (%s); trying fallback model %s",
                model,
                current_error.code,
                models[index + 1],
            )
            last_error = current_error
            continue

        if current_error.code == "GEMINI_API_ERROR":
            logger.exception("Gemini visual review request failed")
        else:
            logger.warning(
                "Gemini visual review unavailable on model %s: %s",
                model,
                current_error.code,
            )
        raise current_error

    # The loop always raises or returns, but keep an explicit safe failure guard.
    raise last_error or GeminiServiceError(
        "GEMINI_API_ERROR", "The visual review service failed to respond."
    )
