"""Pydantic models for API requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from core.review_schemas import (
    UnifiedResumeReviewResponse,
    VisualReviewResponse,
)


class ResumeAnalysisRequest(BaseModel):
    file_base64: str = Field(..., description="Base64 encoded resume file")
    file_type: str = Field(..., description="File extension (pdf, docx, jpg, png, etc.)")
    job_description: Optional[str] = Field(default="", description="Optional job description")


class VisualReviewRequest(BaseModel):
    file_base64: str = Field(..., description="Base64 encoded resume file")
    file_type: str = Field(..., description="File extension (pdf, docx, jpg, or png)")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty")
        return value


class ChatResponse(BaseModel):
    response: str


class HealthResponse(BaseModel):
    status: str


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "HealthResponse",
    "ResumeAnalysisRequest",
    "UnifiedResumeReviewResponse",
    "VisualReviewRequest",
    "VisualReviewResponse",
]
