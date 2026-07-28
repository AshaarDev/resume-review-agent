"""Resume-specific visual review orchestration."""

from pathlib import Path
from typing import List

from core.review_schemas import (
    LayoutAnalysisResponse,
    ReviewStatus,
    VisualReviewResult,
)
from core.policy_schemas import ResumeQualityPolicy
from services.gemini_service import analyze_images_structured
from services.policy_prompt_builder import build_visual_policy_instructions
from services.resume_policy import get_resume_quality_policy

VISUAL_REVIEW_PROMPT = """Review every supplied resume page as a professional
resume designer and recruiter. Evaluate overall professionalism, spacing,
alignment, font consistency and hierarchy, readability, crowding, whitespace
balance, section organization, bullet alignment, date alignment, and
multi-page consistency.

Before scoring, identify pages that contain no meaningful resume content.
Ignore completely blank pages, including trailing pages introduced by document
conversion. Do not include blank pages in the visual score, whitespace issues,
page-count judgment, or multi-page consistency findings. A blank page by itself
is not a resume design defect. In particular, when the document renders as two
pages but the second page is blank, treat the resume as a one-page resume. Count
and review the second page only when it contains actual resume text or other
meaningful resume content.

Base the score and findings only on visible evidence. Provide concise,
actionable strengths and issues. Assign the most specific stable issue code
available in the response schema. Use OTHER only when no specific code fits.
Critical issues prevent effective reading, major issues materially reduce
professionalism, and minor issues are polish improvements."""


def exclude_blank_document_pages(
    image_paths: List[Path],
    layout_data: LayoutAnalysisResponse,
    *,
    text_metrics_available: bool,
) -> tuple[List[Path], LayoutAnalysisResponse]:
    """Exclude truly blank PDF/DOCX pages while retaining original page numbers."""

    if (
        not text_metrics_available
        or layout_data.status != ReviewStatus.AVAILABLE
        or len(layout_data.pages) != len(image_paths)
    ):
        return image_paths, layout_data

    reviewable_indexes = [
        index
        for index, page in enumerate(layout_data.pages)
        if page.font_sizes or page.text_density > 0.001
    ]
    # If the entire document has no extractable text, keep the images so Gemini
    # can still review scanned/image-based resumes.
    if not reviewable_indexes:
        return image_paths, layout_data

    filtered_paths = [image_paths[index] for index in reviewable_indexes]
    filtered_pages = [layout_data.pages[index] for index in reviewable_indexes]
    return (
        filtered_paths,
        layout_data.model_copy(
            update={
                "page_count": len(filtered_pages),
                "pages": filtered_pages,
            }
        ),
    )


def review_resume_visually(
    image_paths: List[Path],
    layout_data: LayoutAnalysisResponse,
    policy: ResumeQualityPolicy | None = None,
) -> VisualReviewResult:
    """Review rendered resume pages with Gemini and deterministic context."""

    active_policy = policy or get_resume_quality_policy()
    return analyze_images_structured(
        image_paths=image_paths,
        prompt=(
            VISUAL_REVIEW_PROMPT
            + "\n\n"
            + build_visual_policy_instructions(active_policy)
        ),
        layout_context=layout_data.model_dump(mode="json"),
    )
