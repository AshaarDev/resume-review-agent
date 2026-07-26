"""API routes for independent and unified resume reviews."""

from fastapi import APIRouter, HTTPException

from core.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ResumeAnalysisRequest,
    UnifiedResumeReviewResponse,
    VisualReviewRequest,
    VisualReviewResponse,
)
from services.openai_service import run_chat
from services.document_processor import (
    DocumentProcessingError,
    decode_resume_file,
    normalize_file_type,
)
from services.review_orchestrator import (
    analyze_resume_bytes,
    analyze_visual_bytes,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Chat with the AI assistant."""
    try:
        response_text = run_chat(request.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI service failed to respond. Please try again.",
        ) from exc

    return ChatResponse(response=response_text)


def _decode_request(file_base64: str, file_type: str) -> tuple[bytes, str]:
    try:
        normalized_type = normalize_file_type(file_type)
        file_bytes = decode_resume_file(file_base64)
        return file_bytes, normalized_type
    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.post(
    "/analyze-resume",
    response_model=UnifiedResumeReviewResponse,
)
def analyze_resume(request: ResumeAnalysisRequest) -> UnifiedResumeReviewResponse:
    """Return content, visual, and deterministic layout reviews together."""

    file_bytes, file_type = _decode_request(
        request.file_base64, request.file_type
    )
    return analyze_resume_bytes(
        file_bytes, file_type, request.job_description or ""
    )


@router.post(
    "/analyze-resume-visual",
    response_model=VisualReviewResponse,
)
def analyze_resume_visual(request: VisualReviewRequest) -> VisualReviewResponse:
    """Run only the visual branch for development and troubleshooting."""

    file_bytes, file_type = _decode_request(
        request.file_base64, request.file_type
    )
    return analyze_visual_bytes(file_bytes, file_type)
