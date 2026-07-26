"""Visual prompt orchestration tests."""

from pathlib import Path

from core.review_schemas import (
    LayoutAnalysisResponse,
    ReviewStatus,
    VisualReviewResult,
)
from services import visual_reviewer


def test_visual_reviewer_passes_images_and_layout(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "page_1.png"
    image_path.write_bytes(b"png")
    expected = VisualReviewResult(
        visual_score=75,
        pass_status=True,
        strengths=[],
        issues=[],
    )
    captured = {}

    def fake_analyze(image_paths, prompt, layout_context):
        captured.update(
            image_paths=image_paths,
            prompt=prompt,
            layout_context=layout_context,
        )
        return expected

    monkeypatch.setattr(
        visual_reviewer, "analyze_images_structured", fake_analyze
    )
    layout = LayoutAnalysisResponse(
        status=ReviewStatus.AVAILABLE, page_count=1
    )

    result = visual_reviewer.review_resume_visually([image_path], layout)

    assert result == expected
    assert captured["image_paths"] == [image_path]
    assert "whitespace" in captured["prompt"]
    assert captured["layout_context"]["status"] == "available"
