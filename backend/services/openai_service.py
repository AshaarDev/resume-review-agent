"""OpenAI integration for chat completions."""

from typing import Optional
import httpx
from openai import OpenAI

from core.config import settings


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI client instance."""
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        
        # Create httpx client without proxies to avoid compatibility issues
        http_client = httpx.Client()
        _client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client
        )
    return _client


def run_chat(message: str) -> str:
    """Run a chat completion and return the response text."""
    client = get_client()

    response = client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=[
            {"role": "system", "content": settings.SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content or "I was unable to generate a response."
