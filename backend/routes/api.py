"""API routes for independent and unified resume reviews."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

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
        return run_resume_workflow(**_workflow_arguments(request))
    except DocumentProcessingError:
        # Already handled by _decode_request
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The workflow could not be started. Please try again.",
        ) from exc


def _workflow_arguments(request: ResumeWorkflowRequest) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "intent": request.intent,
        "job_description": request.job_description,
        "user_instructions": request.user_instructions,
    }
    if request.intent.value == "review":
        file_bytes, file_type = _decode_request(
            request.file_base64 or "", request.file_type or ""
        )
        arguments.update(file_bytes=file_bytes, file_type=file_type)
    else:
        arguments["creation_brief"] = request.creation_brief
    return arguments


def _encode_sse(event_name: str, payload: dict[str, Any]) -> str:
    return (
        f"event: {event_name}\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )


@router.post("/resume-workflows/stream")
async def stream_resume_workflow(
    request: ResumeWorkflowRequest,
) -> StreamingResponse:
    """Stream sanitized, request-scoped workflow events and the final result."""

    arguments = _workflow_arguments(request)

    async def event_stream():
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        sequence = 0

        def event_sink(event: dict[str, Any]) -> None:
            nonlocal sequence
            sequence += 1
            payload = {
                "sequence": sequence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event,
            }
            loop.call_soon_threadsafe(
                queue.put_nowait, ("progress", payload)
            )

        async def execute() -> None:
            try:
                result = await asyncio.to_thread(
                    run_resume_workflow,
                    **arguments,
                    event_sink=event_sink,
                )
                await queue.put(("result", result.model_dump(mode="json")))
            except Exception:
                await queue.put(
                    (
                        "error",
                        {
                            "code": "WORKFLOW_STREAM_FAILED",
                            "message": (
                                "The workflow stream stopped unexpectedly. "
                                "Please try again."
                            ),
                        },
                    )
                )

        worker = asyncio.create_task(execute())
        try:
            while True:
                try:
                    event_name, payload = await asyncio.wait_for(
                        queue.get(), timeout=15
                    )
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _encode_sse(event_name, payload)
                if event_name in {"result", "error"}:
                    break
        finally:
            if not worker.done():
                worker.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
