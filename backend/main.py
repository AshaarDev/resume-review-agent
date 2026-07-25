"""Resume Review Agent - FastAPI Application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes.api import router as api_router

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

# Include API routes
app.include_router(api_router)

# Mount frontend static files
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/")
def serve_frontend() -> FileResponse:
    """Serve the frontend HTML."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js")
def serve_js() -> FileResponse:
    """Serve the frontend JavaScript."""
    return FileResponse(FRONTEND_DIR / "app.js")


@app.get("/styles.css")
def serve_css() -> FileResponse:
    """Serve the frontend CSS."""
    return FileResponse(FRONTEND_DIR / "styles.css")
