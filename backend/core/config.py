"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment."""
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_VISION_MODEL: str = os.getenv(
        "GEMINI_VISION_MODEL", "gemini-3.6-flash"
    )
    GEMINI_TIMEOUT_SECONDS: int = int(
        os.getenv("GEMINI_TIMEOUT_SECONDS", "60")
    )

    MAX_RESUME_FILE_BYTES: int = int(
        os.getenv("MAX_RESUME_FILE_BYTES", str(10 * 1024 * 1024))
    )
    MAX_RESUME_PAGES: int = int(os.getenv("MAX_RESUME_PAGES", "5"))
    MAX_VISION_IMAGE_PIXELS: int = int(
        os.getenv("MAX_VISION_IMAGE_PIXELS", "16000000")
    )
    MAX_VISION_IMAGE_DIMENSION: int = int(
        os.getenv("MAX_VISION_IMAGE_DIMENSION", "4096")
    )
    DOCUMENT_RENDER_DPI: int = int(os.getenv("DOCUMENT_RENDER_DPI", "144"))
    DOCX_CONVERSION_TIMEOUT_SECONDS: int = int(
        os.getenv("DOCX_CONVERSION_TIMEOUT_SECONDS", "60")
    )
    MCP_ALLOWED_FILE_ROOTS: str = os.getenv(
        "MCP_ALLOWED_FILE_ROOTS", "uploads"
    )
    
    SYSTEM_PROMPT: str = """You are a helpful resume review assistant.

Your role is to help users create and improve their resumes.

Keep your responses clear, professional, and actionable.
"""


settings = Settings()
