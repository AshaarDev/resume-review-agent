"""Google GenAI client configuration and structured-output tests."""

from types import SimpleNamespace

import pytest

from core.config import settings
from services import gemini_service
from services.gemini_service import GeminiServiceError, analyze_images_structured


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class SequencedModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_missing_api_key_is_explicit(monkeypatch):
    gemini_service.reset_client()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    with pytest.raises(GeminiServiceError) as exc_info:
        gemini_service.get_client()
    assert exc_info.value.code == "GEMINI_NOT_CONFIGURED"


def test_client_uses_configured_sdk_timeout(monkeypatch):
    from google import genai

    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(models=SimpleNamespace())

    gemini_service.reset_client()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "GEMINI_TIMEOUT_SECONDS", 12)
    monkeypatch.setattr(genai, "Client", fake_client)

    gemini_service.get_client()

    assert captured["api_key"] == "test-key"
    assert captured["http_options"].timeout == 12000
    gemini_service.reset_client()


def test_structured_response_is_validated(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"not-decoded-by-sdk")
    response = SimpleNamespace(
        parsed={
            "visual_score": 88,
            "pass_status": True,
            "strengths": ["Clear hierarchy"],
            "issues": [
                {
                    "code": "INCONSISTENT_ALIGNMENT",
                    "description": "Dates do not share an edge.",
                    "severity": "minor",
                    "affected_area": "page 1",
                    "recommendation": "Use one right-aligned date column.",
                }
            ],
        },
        text=None,
    )
    fake_models = FakeModels(response)
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=fake_models)
    )

    result = analyze_images_structured([image_path], "Review this resume")

    assert result.visual_score == 88
    assert result.issues[0].code.value == "INCONSISTENT_ALIGNMENT"
    assert fake_models.calls[0]["model"] == settings.GEMINI_VISION_MODEL


def test_invalid_structured_response_is_unavailable(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    fake_models = FakeModels(
        SimpleNamespace(parsed={"visual_score": 101}, text=None)
    )
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=fake_models)
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_images_structured([image_path], "Review")
    assert exc_info.value.code == "GEMINI_INVALID_RESPONSE"


def test_timeout_is_categorized(monkeypatch, tmp_path):
    class TimeoutModels:
        def generate_content(self, **kwargs):
            raise TimeoutError("request timed out")

    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=TimeoutModels())
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_images_structured([image_path], "Review")
    assert exc_info.value.code == "GEMINI_TIMEOUT"


def test_unavailable_model_is_categorized(monkeypatch, tmp_path):
    class MissingModel:
        def generate_content(self, **kwargs):
            raise RuntimeError(
                "404 NOT_FOUND: This model is no longer available."
            )

    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=MissingModel())
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_images_structured([image_path], "Review")
    assert exc_info.value.code == "GEMINI_MODEL_UNAVAILABLE"


def test_transient_primary_failure_uses_configured_fallback(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    valid_response = SimpleNamespace(
        parsed={
            "visual_score": 91,
            "pass_status": True,
            "strengths": ["Clear layout"],
            "issues": [],
        },
        text=None,
    )
    models = SequencedModels(
        [
            RuntimeError("503 UNAVAILABLE: model is experiencing high demand"),
            valid_response,
        ]
    )
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=models)
    )
    monkeypatch.setattr(settings, "GEMINI_VISION_MODEL", "primary-model")
    monkeypatch.setattr(
        settings, "GEMINI_VISION_FALLBACK_MODEL", "fallback-model"
    )

    result = analyze_images_structured([image_path], "Review")

    assert result.visual_score == 91
    assert [call["model"] for call in models.calls] == [
        "primary-model",
        "fallback-model",
    ]


def test_authentication_failure_does_not_use_fallback(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    models = SequencedModels([RuntimeError("401 UNAUTHORIZED")])
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=models)
    )
    monkeypatch.setattr(settings, "GEMINI_VISION_MODEL", "primary-model")
    monkeypatch.setattr(
        settings, "GEMINI_VISION_FALLBACK_MODEL", "fallback-model"
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_images_structured([image_path], "Review")

    assert exc_info.value.code == "GEMINI_AUTHENTICATION_FAILED"
    assert [call["model"] for call in models.calls] == ["primary-model"]


def test_duplicate_fallback_model_is_not_called_twice(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"bytes")
    models = SequencedModels([TimeoutError("request timed out")])
    monkeypatch.setattr(
        gemini_service, "_client", SimpleNamespace(models=models)
    )
    monkeypatch.setattr(settings, "GEMINI_VISION_MODEL", "same-model")
    monkeypatch.setattr(
        settings, "GEMINI_VISION_FALLBACK_MODEL", "same-model"
    )

    with pytest.raises(GeminiServiceError) as exc_info:
        analyze_images_structured([image_path], "Review")

    assert exc_info.value.code == "GEMINI_TIMEOUT"
    assert len(models.calls) == 1
