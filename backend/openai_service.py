"""OpenAI integration for basic chat."""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from backend.system_prompt import SYSTEM_PROMPT

load_dotenv()

MODEL_NAME = "gpt-4o-mini"

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client


def run_chat(message: str) -> str:
    """Run a basic chat completion and return the response text."""
    client = get_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content or "I was unable to generate a response."
