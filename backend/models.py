from pydantic import BaseModel, Field, field_validator


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
