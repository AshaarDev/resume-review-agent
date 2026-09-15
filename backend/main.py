"""Resume Intelligence Agents - FastAPI application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes.api import router as api_router
from routes.builder import router as builder_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
REACT_DIST_DIR = FRONTEND_DIR / "frontend-app" / "dist"
SERVED_FRONTEND_DIR = (
    REACT_DIST_DIR if (REACT_DIST_DIR / "index.html").is_file() else FRONTEND_DIR
)

app = FastAPI(title="Resume Intelligence Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Page-Count"],
)

# Include API routes
app.include_router(api_router)
app.include_router(builder_router)

# Vite emits production assets into ``dist/assets``. The legacy static
# directory remains a local fallback until a React build has been generated.
ASSETS_DIR = SERVED_FRONTEND_DIR / "assets"
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/")
def serve_frontend() -> FileResponse:
    """Serve the React frontend (or the legacy local fallback)."""
    return FileResponse(SERVED_FRONTEND_DIR / "index.html")


@app.get("/signin")
@app.get("/app")
def serve_react_route() -> FileResponse:
    """Return the React entry point for client-side routes."""
    return FileResponse(SERVED_FRONTEND_DIR / "index.html")
