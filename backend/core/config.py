"""Application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment."""
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    
    SYSTEM_PROMPT: str = """You are a helpful resume review assistant.

Your role is to help users create and improve their resumes.

Keep your responses clear, professional, and actionable.
"""


settings = Settings()
