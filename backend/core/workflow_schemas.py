"""Workflow schemas for LangGraph orchestration."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.review_schemas import (
    ContentReviewResponse,
    LayoutAnalysisResponse,
    VisualReviewResponse,
)


class WorkflowIntent(str, Enum):
    """Supported workflow intents."""

    REVIEW = "review"
    CREATE = "create"
    REVISE = "revise"


class WorkflowStatus(str, Enum):
    """Overall workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_IMPLEMENTED = "not_implemented"


class AgentStatus(str, Enum):
    """Individual agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_INVOKED = "not_invoked"


class ResumeWorkflowRequest(BaseModel):
    """Request to initiate a resume workflow."""

    intent: WorkflowIntent = WorkflowIntent.REVIEW
    file_base64: str = Field(..., description="Base64 encoded resume file")
    file_type: str = Field(..., description="File extension (pdf, docx, jpg, png, etc.)")
    job_description: str = Field(default="", description="Optional job description")
    user_instructions: str = Field(default="", description="Optional user instructions")


class PriorityAction(BaseModel):
    """A prioritized action extracted from review findings."""

    priority: int = Field(ge=1, description="Priority level (1=highest)")
    source: str = Field(description="Source: content, visual, or layout")
    issue_code: Optional[str] = Field(default=None, description="Stable issue code if applicable")
    title: str = Field(min_length=1, description="Action title")
    recommendation: str = Field(min_length=1, description="Specific recommendation")


class ReviewAgentResult(BaseModel):
    """Structured result from the Resume Review Agent."""

    status: AgentStatus
    content_review: ContentReviewResponse
    visual_review: VisualReviewResponse
    layout_analysis: LayoutAnalysisResponse
    proposed_actions: list[PriorityAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class OrchestratorSummary(BaseModel):
    """Final synthesis from the orchestrator model."""

    overall_assessment: str = Field(min_length=1)
    top_strengths: list[str] = Field(default_factory=list, max_length=3)
    priority_actions: list[PriorityAction] = Field(default_factory=list, max_length=5)
    next_step: str = Field(min_length=1)


class ResumeWorkflowResponse(BaseModel):
    """Complete workflow response returned to API or MCP client."""

    workflow_id: str
    intent: WorkflowIntent
    status: WorkflowStatus

    final_message: str
    summary: OrchestratorSummary

    review: ReviewAgentResult
    agent_statuses: dict[str, AgentStatus]

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
