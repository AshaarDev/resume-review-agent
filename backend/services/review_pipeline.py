"""Shared resume-review workflow used by FastAPI and MCP tools."""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from core.config import settings
from core.review_schemas import (
    ContentReviewResponse,
    LayoutAnalysisResponse,
    ReviewStatus,
    UnifiedResumeReviewResponse,
    VisualReviewResponse,
)
from services.document_processor import (
    DocumentProcessingError,
    PreparedDocument,
    normalize_file_type,
    prepare_resume_for_vision,
    resume_workspace,
    validate_resume_bytes,
)
from services.gemini_service import GeminiServiceError
from services.layout_analyzer import analyze_layout
from services.openai_service import run_chat
from services.resume_parser import ResumeParser
from services.visual_reviewer import review_resume_visually

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parent.parent


def content_review(
    source_path: Path, job_description: str = ""
) -> ContentReviewResponse:
    """Extract text and run the independent GPT content review."""

    parsed_data = ResumeParser.parse_resume(str(source_path))
    if not parsed_data["success"]:
        return ContentReviewResponse(
            status=ReviewStatus.UNAVAILABLE,
            error_code="TEXT_EXTRACTION_FAILED",
            error_message="Resume text could not be extracted.",
        )

    resume_text = parsed_data["text"]
    prompt = f"Please review this resume and provide detailed feedback:\n\n{resume_text}"
    if job_description:
        prompt += (
            f"\n\nJob Description:\n{job_description}\n\n"
            "Please tailor your feedback to this job description."
        )
    try:
        return ContentReviewResponse(
            status=ReviewStatus.AVAILABLE,
            response=run_chat(prompt),
        )
    except Exception:
        logger.exception("OpenAI content review failed")
        return ContentReviewResponse(
            status=ReviewStatus.UNAVAILABLE,
            error_code="CONTENT_REVIEW_FAILED",
            error_message="The content review service is unavailable.",
        )


def unavailable_visual(
    code: str, message: str, page_count: Optional[int] = None
) -> VisualReviewResponse:
    return VisualReviewResponse(
        status=ReviewStatus.UNAVAILABLE,
        error_code=code,
        error_message=message,
        page_count=page_count,
    )


def unavailable_layout(code: str, message: str) -> LayoutAnalysisResponse:
    return LayoutAnalysisResponse(
        status=ReviewStatus.UNAVAILABLE,
        error_code=code,
        error_message=message,
    )


def run_visual_branches(
    source_path: Path, file_type: str, workspace_path: Path
) -> Tuple[VisualReviewResponse, LayoutAnalysisResponse, Optional[PreparedDocument]]:
    """Prepare once, then run deterministic layout and Gemini vision reviews."""

    try:
        prepared = prepare_resume_for_vision(
            source_path, file_type, workspace_path
        )
    except DocumentProcessingError as exc:
        return (
            unavailable_visual(exc.code, str(exc)),
            unavailable_layout(exc.code, str(exc)),
            None,
        )

    try:
        layout = analyze_layout(prepared)
    except DocumentProcessingError as exc:
        layout = unavailable_layout(exc.code, str(exc))

    try:
        result = review_resume_visually(prepared.page_image_paths, layout)
        visual = VisualReviewResponse(
            status=ReviewStatus.AVAILABLE,
            result=result,
            page_count=prepared.page_count,
        )
    except GeminiServiceError as exc:
        visual = unavailable_visual(
            exc.code, str(exc), page_count=prepared.page_count
        )
    except Exception:
        logger.exception("Unexpected visual review failure")
        visual = unavailable_visual(
            "VISUAL_REVIEW_FAILED",
            "The visual review service is unavailable.",
            page_count=prepared.page_count,
        )
    return visual, layout, prepared


def analyze_resume_bytes(
    file_bytes: bytes,
    file_type: str,
    job_description: str = "",
) -> UnifiedResumeReviewResponse:
    """Run the complete workflow while one context owns all temporary files."""

    started_at = time.perf_counter()
    normalized_type = normalize_file_type(file_type)
    validate_resume_bytes(file_bytes)
    with resume_workspace() as workspace:
        source_path = workspace.save_upload(file_bytes, normalized_type)
        content = content_review(source_path, job_description)
        visual, layout, prepared = run_visual_branches(
            source_path, normalized_type, workspace.path
        )
        response = UnifiedResumeReviewResponse(
            content_review=content,
            visual_review=visual,
            layout_analysis=layout,
            metadata={
                "file_type": normalized_type,
                "file_size_bytes": len(file_bytes),
                "page_count": prepared.page_count if prepared else None,
                "processing_time_ms": round(
                    (time.perf_counter() - started_at) * 1000, 2
                ),
            },
        )
    return response


def analyze_visual_bytes(
    file_bytes: bytes, file_type: str
) -> VisualReviewResponse:
    """Run document preparation, layout context, and Gemini visual review."""

    normalized_type = normalize_file_type(file_type)
    validate_resume_bytes(file_bytes)
    with resume_workspace() as workspace:
        source_path = workspace.save_upload(file_bytes, normalized_type)
        visual, _, _ = run_visual_branches(
            source_path, normalized_type, workspace.path
        )
        response = visual
    return response


def analyze_layout_bytes(
    file_bytes: bytes, file_type: str
) -> LayoutAnalysisResponse:
    """Run only deterministic preparation and layout analysis."""

    normalized_type = normalize_file_type(file_type)
    validate_resume_bytes(file_bytes)
    with resume_workspace() as workspace:
        source_path = workspace.save_upload(file_bytes, normalized_type)
        try:
            prepared = prepare_resume_for_vision(
                source_path, normalized_type, workspace.path
            )
            response = analyze_layout(prepared)
        except DocumentProcessingError as exc:
            response = unavailable_layout(exc.code, str(exc))
    return response


def load_resume_file(file_path: str) -> Tuple[bytes, str]:
    """Read an MCP file only when it resolves inside an approved root."""

    path = Path(file_path).expanduser().resolve(strict=False)
    allowed_roots = []
    for configured_root in settings.MCP_ALLOWED_FILE_ROOTS.split(","):
        configured_root = configured_root.strip()
        if not configured_root:
            continue
        root = Path(configured_root).expanduser()
        if not root.is_absolute():
            root = BACKEND_DIR / root
        allowed_roots.append(root.resolve(strict=False))

    if not allowed_roots:
        raise DocumentProcessingError(
            "MCP_FILE_ROOTS_NOT_CONFIGURED",
            "Path-based MCP resume tools have no approved file roots.",
        )
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise DocumentProcessingError(
            "FILE_PATH_NOT_ALLOWED",
            "The requested resume must be inside an approved MCP upload directory.",
        )
    if not path.is_file():
        raise DocumentProcessingError(
            "FILE_NOT_FOUND", "The requested resume file does not exist."
        )
    file_type = normalize_file_type(path.suffix)
    file_size = path.stat().st_size
    if file_size > settings.MAX_RESUME_FILE_BYTES:
        raise DocumentProcessingError(
            "FILE_TOO_LARGE",
            "The requested resume exceeds the configured file-size limit.",
        )
    file_bytes = path.read_bytes()
    validate_resume_bytes(file_bytes)
    return file_bytes, file_type


def analyze_resume_file(
    file_path: str, job_description: str = ""
) -> UnifiedResumeReviewResponse:
    file_bytes, file_type = load_resume_file(file_path)
    return analyze_resume_bytes(file_bytes, file_type, job_description)


def analyze_visual_file(file_path: str) -> VisualReviewResponse:
    file_bytes, file_type = load_resume_file(file_path)
    return analyze_visual_bytes(file_bytes, file_type)


def analyze_layout_file(file_path: str) -> LayoutAnalysisResponse:
    file_bytes, file_type = load_resume_file(file_path)
    return analyze_layout_bytes(file_bytes, file_type)
