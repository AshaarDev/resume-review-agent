"""Shared contracts for resume workflows, agents, and synthesis."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from core.review_schemas import (
    ContentReviewResponse,
    LayoutAnalysisResponse,
    VisualReviewResponse,
)
from core.policy_schemas import PolicyFinding


class WorkflowIntent(str, Enum):
    REVIEW = "review"
    CREATE = "create"
    REVISE = "revise"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_IMPLEMENTED = "not_implemented"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_INVOKED = "not_invoked"


class WorkflowMessage(BaseModel):
    """A safe, stable warning or error exposed by a workflow."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    source: Optional[str] = None


class ResumeWorkflowRequest(BaseModel):
    """A future-ready workflow request with review-specific file validation."""

    intent: WorkflowIntent = WorkflowIntent.REVIEW
    file_base64: Optional[str] = None
    file_type: Optional[str] = None
    job_description: str = ""
    user_instructions: str = ""

    @model_validator(mode="after")
    def require_review_document(self) -> "ResumeWorkflowRequest":
        if self.intent == WorkflowIntent.REVIEW:
            if not self.file_base64 or not self.file_type:
                raise ValueError(
                    "file_base64 and file_type are required for review workflows"
                )
        return self


class PriorityAction(BaseModel):
    """A normalized action that can later be consumed by the Creator Agent."""

    priority: int = Field(ge=1)
    source: str
    issue_code: Optional[str] = None
    title: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ReviewAgentResult(BaseModel):
    """Raw branch results plus normalized, prioritized review actions."""

    status: AgentStatus
    content_review: ContentReviewResponse
    visual_review: VisualReviewResponse
    layout_analysis: LayoutAnalysisResponse
    policy_id: str
    policy_version: str
    policy_findings: list[PolicyFinding] = Field(default_factory=list)
    proposed_actions: list[PriorityAction] = Field(default_factory=list)
    warnings: list[WorkflowMessage] = Field(default_factory=list)
    errors: list[WorkflowMessage] = Field(default_factory=list)


class OrchestratorSummary(BaseModel):
    """Validated synthesis used to build the final user-facing message."""

    overall_assessment: str = Field(min_length=1)
    top_strengths: list[str] = Field(default_factory=list)
    priority_actions: list[PriorityAction] = Field(default_factory=list)
    next_step: str = Field(min_length=1)


class OrchestratorSynthesisResult(BaseModel):
    """Synthesis plus explicit metadata about deterministic fallback."""

    summary: OrchestratorSummary
    warnings: list[WorkflowMessage] = Field(default_factory=list)


class ResumeWorkflowResponse(BaseModel):
    """Public workflow response; temporary artifacts are intentionally absent."""

    workflow_id: str
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    intent: WorkflowIntent
    status: WorkflowStatus
    final_message: str
    summary: Optional[OrchestratorSummary] = None
    review: Optional[ReviewAgentResult] = None
    agent_statuses: dict[str, AgentStatus]
    warnings: list[WorkflowMessage] = Field(default_factory=list)
    errors: list[WorkflowMessage] = Field(default_factory=list)
