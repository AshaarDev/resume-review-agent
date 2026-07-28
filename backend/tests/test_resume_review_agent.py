"""Resume Review Agent behavior and deterministic-action tests."""

from pathlib import Path

from agents import resume_review_agent
from agents.resume_review_agent import ResumeReviewAgent
from core.review_schemas import (
    UnifiedResumeReviewResponse,
    VisualIssue,
    VisualIssueCode,
    VisualIssueSeverity,
    VisualReviewResult,
)
from core.workflow_schemas import AgentStatus


def _review(**overrides) -> UnifiedResumeReviewResponse:
    data = {
        "content_review": {
            "status": "available",
            "response": "- Improve the summary for the target role.",
        },
        "visual_review": {
            "status": "available",
            "result": VisualReviewResult(
                visual_score=80,
                pass_status=True,
                strengths=["Clear hierarchy"],
                issues=[
                    VisualIssue(
                        code=VisualIssueCode.INCONSISTENT_ALIGNMENT,
                        description="Dates are inconsistently aligned.",
                        severity=VisualIssueSeverity.MAJOR,
                        recommendation="Use one right-aligned date column.",
                    )
                ],
            ),
            "page_count": 1,
        },
        "layout_analysis": {
            "status": "available",
            "page_count": 1,
            "pages": [
                {
                    "page_number": 1,
                    "width_points": 612,
                    "height_points": 792,
                    "text_density": 0.7,
                    "font_sizes": [7, 9],
                    "min_font_size": 7,
                    "median_font_size": 9,
                    "dominant_font_size": 9,
                    "max_font_size": 9,
                }
            ],
        },
        "metadata": {},
    }
    data.update(overrides)
    return UnifiedResumeReviewResponse.model_validate(data)


def test_agent_uses_caller_workspace_and_normalizes_actions(
    monkeypatch, tmp_path: Path
):
    captured = {}

    def fake_pipeline(
        source_path, file_type, job_description, workspace_path, policy
    ):
        captured.update(
            source_path=source_path,
            file_type=file_type,
            job_description=job_description,
            workspace_path=workspace_path,
        )
        return _review()

    monkeypatch.setattr(
        resume_review_agent, "run_review_pipeline", fake_pipeline
    )
    source = tmp_path / "resume.pdf"
    source.write_bytes(b"pdf")
    result = ResumeReviewAgent().run(
        source, "pdf", "Engineer", "", tmp_path
    )

    assert result.status == AgentStatus.COMPLETED
    assert captured["workspace_path"] == tmp_path
    assert {action.issue_code for action in result.proposed_actions} >= {
        "INCONSISTENT_ALIGNMENT",
        "SMALL_BODY_FONT",
        "VERY_SMALL_TEXT",
        "HIGH_TEXT_DENSITY",
        "CONTENT_RECOMMENDATION",
    }
    assert "final_message" not in result.model_dump()


def test_agent_preserves_partial_results_and_structured_warning(
    monkeypatch, tmp_path: Path
):
    review = _review(
        visual_review={
            "status": "unavailable",
            "error_code": "GEMINI_TIMEOUT",
            "error_message": "Visual review timed out.",
        }
    )
    monkeypatch.setattr(
        resume_review_agent,
        "run_review_pipeline",
        lambda *args, **kwargs: review,
    )
    source = tmp_path / "resume.pdf"
    source.write_bytes(b"pdf")
    result = ResumeReviewAgent().run(source, "pdf", "", "", tmp_path)

    assert result.status == AgentStatus.PARTIAL
    assert result.content_review.status.value == "available"
    assert result.warnings[0].code == "GEMINI_TIMEOUT"


def test_image_resume_skips_font_and_density_actions(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(
        resume_review_agent,
        "run_review_pipeline",
        lambda *args, **kwargs: _review(),
    )
    source = tmp_path / "resume.png"
    source.write_bytes(b"image")
    result = ResumeReviewAgent().run(source, "png", "", "", tmp_path)

    layout_codes = {
        action.issue_code
        for action in result.proposed_actions
        if action.source == "layout"
    }
    assert layout_codes == set()


def test_blank_pdf_page_does_not_create_layout_action():
    layout = _review().layout_analysis.model_copy(
        update={
            "page_count": 2,
            "pages": [
                _review().layout_analysis.pages[0],
                _review().layout_analysis.pages[0].model_copy(
                    update={
                        "page_number": 2,
                        "width_points": 400,
                        "height_points": 400,
                        "text_density": 0,
                        "font_sizes": [],
                        "min_font_size": None,
                        "median_font_size": None,
                        "dominant_font_size": None,
                    }
                ),
            ],
        }
    )

    actions = ResumeReviewAgent._layout_actions(layout, "pdf")
    assert "LOW_TEXT_DENSITY" not in {
        action.issue_code for action in actions
    }
    assert "INCONSISTENT_PAGE_DIMENSIONS" not in {
        action.issue_code for action in actions
    }
