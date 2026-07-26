"""Resume-specific visual review orchestration."""

from pathlib import Path
from typing import List

from core.review_schemas import LayoutAnalysisResponse, VisualReviewResult
from services.gemini_service import analyze_images_structured

VISUAL_REVIEW_PROMPT = """Review every supplied resume page as a professional
resume designer and recruiter. Evaluate overall professionalism, spacing,
alignment, font consistency and hierarchy, readability, crowding, whitespace
balance, section organization, bullet alignment, date alignment, and
multi-page consistency.

Base the score and findings only on visible evidence. Provide concise,
actionable strengths and issues. Assign the most specific stable issue code
available in the response schema. Use OTHER only when no specific code fits.
Critical issues prevent effective reading, major issues materially reduce
professionalism, and minor issues are polish improvements."""


def review_resume_visually(
    image_paths: List[Path], layout_data: LayoutAnalysisResponse
) -> VisualReviewResult:
    """Review rendered resume pages with Gemini and deterministic context."""

    return analyze_images_structured(
        image_paths=image_paths,
        prompt=VISUAL_REVIEW_PROMPT,
        layout_context=layout_data.model_dump(mode="json"),
    )
