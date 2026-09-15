"""API routes for independent and unified resume reviews."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from core.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ResumeAnalysisRequest,
    UnifiedResumeReviewResponse,
    VisualReviewRequest,
    VisualReviewResponse,
)
from core.workflow_schemas import ResumeWorkflowRequest, ResumeWorkflowResponse
from services.openai_service import run_chat
from services.document_processor import (
    DocumentProcessingError,
    decode_resume_file,
    normalize_file_type,
)
from services.review_pipeline import (
    analyze_resume_bytes,
    analyze_visual_bytes,
)
from workflows.resume_workflow import run_resume_workflow
from services.artifact_store import resolve_artifact
from services.latex_compiler import latex_compiler_available

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        latex_compiler_available=latex_compiler_available(),
    )


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


@router.post(
    "/resume-workflows",
    response_model=ResumeWorkflowResponse,
)
def create_resume_workflow(request: ResumeWorkflowRequest) -> ResumeWorkflowResponse:
    """Route review and creation requests through the shared LangGraph."""
    try:
        if request.intent.value != "review":
            return run_resume_workflow(
                intent=request.intent,
                job_description=request.job_description,
                user_instructions=request.user_instructions,
                creation_brief=request.creation_brief,
            )
        file_bytes, file_type = _decode_request(
            request.file_base64 or "", request.file_type or ""
        )
        return run_resume_workflow(
            intent=request.intent,
            file_bytes=file_bytes,
            file_type=file_type,
            job_description=request.job_description,
            user_instructions=request.user_instructions,
        )
    except DocumentProcessingError:
        # Already handled by _decode_request
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The workflow could not be started. Please try again.",
        ) from exc


@router.get("/artifacts/{artifact_id}/{filename}")
def download_resume_artifact(
    artifact_id: str, filename: str, preview: bool = False
) -> FileResponse:
    """Download only an allowlisted generated resume artifact."""

    path = resolve_artifact(artifact_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    media_type = {".pdf": "application/pdf", ".tex": "application/x-tex",
                  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}[path.suffix]
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type=(
            "inline" if preview and path.suffix == ".pdf" else "attachment"
        ),
    )


@router.get("/artifact-previews/{artifact_id}.png")
def preview_resume_artifact(artifact_id: str) -> Response:
    """Render the first generated PDF page as a browser-safe PNG preview."""

    path = resolve_artifact(artifact_id, "resume.pdf")
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        import fitz

        with fitz.open(path) as document:
            if document.page_count == 0:
                raise ValueError("PDF contains no pages")
            pixmap = document[0].get_pixmap(
                matrix=fitz.Matrix(2.0, 2.0),
                alpha=False,
            )
            image_bytes = pixmap.tobytes("png")
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="The generated PDF could not be rendered for preview.",
        ) from exc
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )
