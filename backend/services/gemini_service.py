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


def _classify_api_error(exc: Exception) -> GeminiServiceError:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if (
        "not_found" in message
        or "no longer available" in message
        or ("404" in message and "model" in message)
    ):
        return GeminiServiceError(
            "GEMINI_MODEL_UNAVAILABLE",
            f"The configured Gemini model '{settings.GEMINI_VISION_MODEL}' "
            "is not available for this API account.",
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
    return GeminiServiceError(
        "GEMINI_API_ERROR", "The visual review service failed to respond."
    )


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

    try:
        response = get_client().models.generate_content(
            model=settings.GEMINI_VISION_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VisualReviewResult,
            ),
        )
    except GeminiServiceError:
        raise
    except Exception as exc:
        classified_error = _classify_api_error(exc)
        if classified_error.code == "GEMINI_API_ERROR":
            logger.exception("Gemini visual review request failed")
        else:
            logger.warning(
                "Gemini visual review unavailable: %s",
                classified_error.code,
            )
        raise classified_error from exc

    try:
        if response.parsed is not None:
            return VisualReviewResult.model_validate(response.parsed)
        if not response.text:
            raise ValueError("Gemini returned an empty response")
        return VisualReviewResult.model_validate_json(response.text)
    except (ValidationError, ValueError, TypeError) as exc:
        logger.warning("Invalid Gemini structured response: %s", exc)
        raise GeminiServiceError(
            "GEMINI_INVALID_RESPONSE",
            "The visual review service returned an invalid structured response.",
        ) from exc
