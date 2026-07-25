from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import ChatRequest, ChatResponse, HealthResponse, ResumeAnalysisRequest
from openai_service import run_chat
import sys
sys.path.insert(0, str(Path(__file__).parent / "mcp" / "servers"))
from resume_parser import ResumeParser

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Resume Review Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/")
def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js")
def serve_js() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js")


@app.get("/styles.css")
def serve_css() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css")


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
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


@app.post("/api/analyze-resume", response_model=ChatResponse)
def analyze_resume(request: ResumeAnalysisRequest) -> ChatResponse:
    try:
        # Parse the resume from base64
        print(f"Parsing resume of type: {request.file_type}")
        parsed_data = ResumeParser.parse_from_base64(request.file_base64, request.file_type)
        
        if not parsed_data["success"]:
            error_msg = parsed_data.get('error', 'Unknown error')
            print(f"Parse error: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse resume: {error_msg}"
            )
        
        # Build prompt for LLM
        resume_text = parsed_data["text"]
        print(f"Extracted text length: {len(resume_text)} characters")
        prompt = f"Please review this resume and provide detailed feedback:\n\n{resume_text}"
        
        if request.job_description:
            prompt += f"\n\nJob Description:\n{request.job_description}\n\nPlease tailor your feedback to this job description."
        
        # Get AI analysis
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
