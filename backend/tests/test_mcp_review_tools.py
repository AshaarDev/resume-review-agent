"""Registration and behavior tests for review and vision MCP tools."""

import asyncio
import base64
from types import SimpleNamespace

from core.review_schemas import (
    LayoutAnalysisResponse,
    ReviewStatus,
    UnifiedResumeReviewResponse,
    VisualReviewResult,
    VisualReviewResponse,
)
from mcp_server import resume_server


def test_review_and_vision_tools_are_registered():
    tools = asyncio.run(resume_server.mcp.list_tools())
    names = {tool.name for tool in tools}

    assert {
        "analyze_resume_layout",
        "analyze_resume_layout_base64",
        "review_resume_visual",
        "review_resume_visual_base64",
        "review_resume_unified",
        "review_resume_unified_base64",
    }.issubset(names)


def test_layout_base64_tool_uses_shared_orchestrator(monkeypatch):
    captured = {}

    def fake_layout(file_bytes, file_type):
        captured.update(file_bytes=file_bytes, file_type=file_type)
        return LayoutAnalysisResponse(
            status=ReviewStatus.AVAILABLE,
            page_count=1,
        )

    monkeypatch.setattr(resume_server, "analyze_layout_bytes", fake_layout)
    result = resume_server.analyze_resume_layout_base64(
        base64.b64encode(b"pdf bytes").decode(), "PDF"
    )

    assert result["status"] == "available"
    assert captured == {"file_bytes": b"pdf bytes", "file_type": "pdf"}


def test_visual_file_tool_preserves_unavailable_status(monkeypatch):
    monkeypatch.setattr(
        resume_server,
        "analyze_visual_file",
        lambda file_path: VisualReviewResponse(
            status=ReviewStatus.UNAVAILABLE,
            error_code="GEMINI_NOT_CONFIGURED",
            error_message="Gemini is unavailable.",
        ),
    )

    result = resume_server.review_resume_visual("resume.pdf")

    assert result["status"] == "unavailable"
    assert result["result"] is None
    assert result["error_code"] == "GEMINI_NOT_CONFIGURED"
    assert "images" not in result
    assert "page_images" not in result
    assert "file_base64" not in result


def test_visual_response_never_contains_rendered_images(monkeypatch):
    monkeypatch.setattr(
        resume_server,
        "analyze_visual_file",
        lambda file_path: VisualReviewResponse(
            status=ReviewStatus.AVAILABLE,
            result=VisualReviewResult(
                visual_score=90,
                pass_status=True,
                strengths=["Clear hierarchy"],
                issues=[],
            ),
            page_count=1,
        ),
    )

    result = resume_server.review_resume_visual("resume.pdf")

    assert set(result) == {
        "status",
        "result",
        "error_code",
        "error_message",
        "page_count",
    }
    assert set(result["result"]) == {
        "visual_score",
        "pass_status",
        "strengths",
        "issues",
    }


def test_unified_file_tool_returns_all_branches(monkeypatch):
    unified = UnifiedResumeReviewResponse(
        content_review={
            "status": "available",
            "response": "Content review",
        },
        visual_review={
            "status": "unavailable",
            "error_code": "GEMINI_TIMEOUT",
            "error_message": "Timed out.",
        },
        layout_analysis={
            "status": "available",
            "page_count": 1,
        },
        metadata={
            "file_type": "pdf",
            "file_size_bytes": 100,
            "page_count": 1,
            "processing_time_ms": 5,
        },
    )
    captured = SimpleNamespace(file_path=None, job_description=None)

    def fake_unified(file_path, job_description):
        captured.file_path = file_path
        captured.job_description = job_description
        return unified

    monkeypatch.setattr(resume_server, "analyze_resume_file", fake_unified)
    result = resume_server.review_resume_unified(
        "resume.pdf", "Backend engineer"
    )

    assert captured.file_path == "resume.pdf"
    assert captured.job_description == "Backend engineer"
    assert result["content_review"]["status"] == "available"
    assert result["visual_review"]["status"] == "unavailable"
    assert result["layout_analysis"]["status"] == "available"


def test_mcp_tool_returns_structured_input_error():
    result = resume_server.review_resume_visual("missing.pdf")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "FILE_PATH_NOT_ALLOWED"
