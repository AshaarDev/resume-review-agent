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
    assert "Ignore completely blank pages" in captured["prompt"]
    assert "treat the resume as a one-page resume" in captured["prompt"]
    assert "only when it contains actual resume text" in captured["prompt"]
    assert "UNBOLDED_KEY_METRICS" in captured["prompt"]
    assert "metric_emphasis" in captured["prompt"]
    assert captured["layout_context"]["status"] == "available"


def test_blank_pdf_pages_are_excluded_from_visual_review(tmp_path: Path):
    paths = []
    for index in range(3):
        path = tmp_path / f"page_{index + 1}.png"
        path.write_bytes(b"png")
        paths.append(path)
    layout = LayoutAnalysisResponse.model_validate(
        {
            "status": "available",
            "page_count": 3,
            "pages": [
                {
                    "page_number": 1,
                    "width_points": 612,
                    "height_points": 792,
                    "text_density": 0.2,
                    "font_sizes": [11],
                },
                {
                    "page_number": 2,
                    "width_points": 612,
                    "height_points": 792,
                    "text_density": 0,
                    "font_sizes": [],
                },
                {
                    "page_number": 3,
                    "width_points": 612,
                    "height_points": 792,
                    "text_density": 0.15,
                    "font_sizes": [10],
                },
            ],
        }
    )

    filtered_paths, filtered_layout = (
        visual_reviewer.exclude_blank_document_pages(
            paths, layout, text_metrics_available=True
        )
    )

    assert filtered_paths == [paths[0], paths[2]]
    assert filtered_layout.page_count == 2
    assert [page.page_number for page in filtered_layout.pages] == [1, 3]


def test_image_only_document_is_not_mistaken_for_blank(tmp_path: Path):
    path = tmp_path / "page_1.png"
    layout = LayoutAnalysisResponse.model_validate(
        {
            "status": "available",
            "page_count": 1,
            "pages": [
                {
                    "page_number": 1,
                    "width_points": 1000,
                    "height_points": 1400,
                    "text_density": 0,
                    "font_sizes": [],
                }
            ],
        }
    )

    filtered_paths, _ = visual_reviewer.exclude_blank_document_pages(
        [path], layout, text_metrics_available=False
    )
    assert filtered_paths == [path]
