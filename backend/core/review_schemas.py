"""Shared schemas for content, visual, and deterministic resume reviews."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Availability of an independently executed review."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class VisualIssueSeverity(str, Enum):
    """Supported visual issue severity levels."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class VisualIssueCode(str, Enum):
    """Stable codes consumed by the frontend and future revision workflows."""

    EXCESSIVE_WHITESPACE = "EXCESSIVE_WHITESPACE"
    INSUFFICIENT_WHITESPACE = "INSUFFICIENT_WHITESPACE"
    INCONSISTENT_ALIGNMENT = "INCONSISTENT_ALIGNMENT"
    INCONSISTENT_FONT_USAGE = "INCONSISTENT_FONT_USAGE"
    WEAK_VISUAL_HIERARCHY = "WEAK_VISUAL_HIERARCHY"
    LOW_READABILITY = "LOW_READABILITY"
    CROWDED_CONTENT = "CROWDED_CONTENT"
    INCONSISTENT_SPACING = "INCONSISTENT_SPACING"
    BULLET_ALIGNMENT = "BULLET_ALIGNMENT"
    DATE_ALIGNMENT = "DATE_ALIGNMENT"
    MULTI_PAGE_INCONSISTENCY = "MULTI_PAGE_INCONSISTENCY"
    OTHER = "OTHER"


class VisualIssue(BaseModel):
    """One actionable problem found in a resume's visual presentation."""

    code: VisualIssueCode
    description: str = Field(min_length=1)
    severity: VisualIssueSeverity
    affected_area: Optional[str] = None
    recommendation: str = Field(min_length=1)


class VisualReviewResult(BaseModel):
    """Validated structured result returned by Gemini."""

    visual_score: int = Field(ge=0, le=100)
    pass_status: bool
    strengths: List[str]
    issues: List[VisualIssue]


class VisualReviewResponse(BaseModel):
    """API wrapper that distinguishes a real result from an unavailable review."""

    status: ReviewStatus
    result: Optional[VisualReviewResult] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    page_count: Optional[int] = None


class ContentReviewResponse(BaseModel):
    """Independent GPT content-review result."""

    status: ReviewStatus
    response: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class LayoutPageMetrics(BaseModel):
    """Deterministic measurements extracted for one page."""

    page_number: int = Field(ge=1)
    width_points: float = Field(gt=0)
    height_points: float = Field(gt=0)
    text_density: float = Field(ge=0, le=1)
    font_sizes: List[float]
    min_font_size: Optional[float] = None
    max_font_size: Optional[float] = None
    median_font_size: Optional[float] = None
    dominant_font_size: Optional[float] = None


class LayoutAnalysisResponse(BaseModel):
    """Required deterministic layout analysis with explicit failure state."""

    status: ReviewStatus
    page_count: Optional[int] = None
    pages: List[LayoutPageMetrics] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class UnifiedResumeReviewResponse(BaseModel):
    """Combined response from independent content, visual, and layout reviews."""

    content_review: ContentReviewResponse
    visual_review: VisualReviewResponse
    layout_analysis: LayoutAnalysisResponse
    metadata: Dict[str, Any]
