"""Unified and isolated visual endpoint integration tests."""

import base64
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from core.review_schemas import VisualReviewResult
from core.policy_schemas import ContentPolicyAnalysis
from main import app
from services import document_processor, review_pipeline
from services.gemini_service import GeminiServiceError

client = TestClient(app)


def _content_analysis() -> ContentPolicyAnalysis:
    return ContentPolicyAnalysis(
        overall_feedback="Strong content.",
        strengths=["Relevant experience"],
        estimated_relevant_experience_years=3,
        experience_estimate_confidence=0.9,
        bullets=[],
    )


def _pdf_base64() -> str:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Jane Candidate")
    data = document.tobytes()
    document.close()
    return base64.b64encode(data).decode()


def test_unified_endpoint_returns_all_review_branches(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    monkeypatch.setattr(
        review_pipeline,
        "run_structured_chat",
        lambda *args, **kwargs: _content_analysis(),
    )
    monkeypatch.setattr(
        review_pipeline,
        "review_resume_visually",
        lambda *args, **kwargs: VisualReviewResult(
            visual_score=91,
            pass_status=True,
            strengths=["Balanced layout"],
            issues=[],
        ),
    )

    response = client.post(
        "/api/analyze-resume",
        json={
            "file_base64": _pdf_base64(),
            "file_type": "pdf",
            "job_description": "",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content_review"]["status"] == "available"
    assert body["visual_review"]["status"] == "available"
    assert body["visual_review"]["result"]["visual_score"] == 91
    assert body["layout_analysis"]["status"] == "available"
    assert body["metadata"]["page_count"] == 1
    assert list(tmp_path.iterdir()) == []


def test_visual_failure_is_explicit_partial_result(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    monkeypatch.setattr(
        review_pipeline,
        "run_structured_chat",
        lambda *args, **kwargs: _content_analysis(),
    )

    def unavailable(*args, **kwargs):
        raise GeminiServiceError("GEMINI_TIMEOUT", "Visual review timed out.")

    monkeypatch.setattr(
        review_pipeline, "review_resume_visually", unavailable
    )
    response = client.post(
        "/api/analyze-resume",
        json={"file_base64": _pdf_base64(), "file_type": "pdf"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content_review"]["status"] == "available"
    assert body["layout_analysis"]["status"] == "available"
    assert body["visual_review"] == {
        "status": "unavailable",
        "result": None,
        "error_code": "GEMINI_TIMEOUT",
        "error_message": "Visual review timed out.",
        "page_count": 1,
    }


def test_visual_only_endpoint_and_invalid_upload(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    monkeypatch.setattr(
        review_pipeline,
        "review_resume_visually",
        lambda *args, **kwargs: VisualReviewResult(
            visual_score=80,
            pass_status=True,
            strengths=[],
            issues=[],
        ),
    )
    response = client.post(
        "/api/analyze-resume-visual",
        json={"file_base64": _pdf_base64(), "file_type": "pdf"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["visual_score"] == 80

    invalid = client.post(
        "/api/analyze-resume-visual",
        json={"file_base64": "not base64!", "file_type": "pdf"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"]["code"] == "INVALID_BASE64"
