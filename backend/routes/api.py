"""API routes for resume analysis and chat."""

from fastapi import APIRouter, HTTPException

from core.models import ChatRequest, ChatResponse, HealthResponse, ResumeAnalysisRequest
from services.openai_service import run_chat
from services.resume_parser import ResumeParser

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


@router.post("/analyze-resume", response_model=ChatResponse)
def analyze_resume(request: ResumeAnalysisRequest) -> ChatResponse:
    """Analyze a resume and provide feedback."""
    try:
        print(f"Parsing resume of type: {request.file_type}")
        parsed_data = ResumeParser.parse_from_base64(request.file_base64, request.file_type)
        
        if not parsed_data["success"]:
            error_msg = parsed_data.get('error', 'Unknown error')
            print(f"Parse error: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse resume: {error_msg}"
            )
        
        resume_text = parsed_data["text"]
        print(f"Extracted text length: {len(resume_text)} characters")
        prompt = f"Please review this resume and provide detailed feedback:\n\n{resume_text}"
        
        if request.job_description:
            prompt += f"\n\nJob Description:\n{request.job_description}\n\nPlease tailor your feedback to this job description."
        
        print("Calling LLM...")
        response_text = run_chat(prompt)
        print("LLM response received")
        
        return ChatResponse(response=response_text)
        
    except HTTPException:
        raise
    except RuntimeError as exc:
        print(f"Runtime error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Exception: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"Error: {str(exc)}",
        ) from exc
