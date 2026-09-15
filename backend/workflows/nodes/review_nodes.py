"""Deterministic intent and Review Agent workflow nodes."""

import logging
from pathlib import Path

from agents.resume_review_agent import ResumeReviewAgent
from core.policy_schemas import ResumeQualityPolicy
from core.workflow_schemas import (
    AgentStatus,
    WorkflowMessage,
    WorkflowStatus,
)
from workflows.state import ResumeWorkflowState
from services.workflow_events import emit_workflow_event

logger = logging.getLogger(__name__)


def validate_intent(state: ResumeWorkflowState) -> dict:
    review_status = AgentStatus.PENDING if state["intent"] == "review" else AgentStatus.NOT_INVOKED
    creator_status = AgentStatus.PENDING if state["intent"] == "create" else AgentStatus.NOT_INVOKED
    return {
        "status": WorkflowStatus.RUNNING.value,
        "agent_statuses": {
            "resume_review_agent": review_status.value,
            "resume_creator_agent": creator_status.value,
        },
        "warnings": [],
        "errors": [],
    }


def run_review_agent(state: ResumeWorkflowState) -> dict:
    emit_workflow_event(
        state.get("event_sink"),
        phase="review_agent",
        status="started",
        message="Resume Review Agent started the content, visual, and layout checks.",
    )
    try:
        arguments = dict(
            source_path=Path(state["source_path"]),
            file_type=state["file_type"],
            job_description=state.get("job_description", ""),
            user_instructions=state.get("user_instructions", ""),
            workspace_path=Path(state["workspace_path"]),
            policy=ResumeQualityPolicy.model_validate(state["policy"]),
        )
        if state.get("event_sink") is not None:
            arguments["event_sink"] = state["event_sink"]
        result = ResumeReviewAgent().run(**arguments)
        emit_workflow_event(
            state.get("event_sink"),
            phase="review_agent",
            status=result.status.value,
            message="Resume Review Agent finished combining the review branches.",
            details={"proposed_actions": len(result.proposed_actions)},
        )
        return {
            "review_result": result.model_dump(mode="json"),
            "agent_statuses": {
                **state["agent_statuses"],
                "resume_review_agent": result.status.value,
            },
            "warnings": [
                message.model_dump(mode="json") for message in result.warnings
            ],
            "errors": [
                message.model_dump(mode="json") for message in result.errors
            ],
        }
    except Exception:
        logger.exception("Review Agent node failed")
        emit_workflow_event(
            state.get("event_sink"),
            phase="review_agent",
            status="failed",
            message="Resume Review Agent could not complete.",
        )
        error = WorkflowMessage(
            code="REVIEW_AGENT_FAILED",
            message="The Resume Review Agent could not complete.",
            source="resume_review_agent",
        )
        return {
            "agent_statuses": {
                **state["agent_statuses"],
                "resume_review_agent": AgentStatus.FAILED.value,
            },
            "errors": [error.model_dump(mode="json")],
        }


def not_implemented(state: ResumeWorkflowState) -> dict:
    message = WorkflowMessage(
        code="WORKFLOW_NOT_IMPLEMENTED",
        message=(
            f"The '{state['intent']}' workflow is reserved for a future "
            "Resume Creator Agent."
        ),
        source="workflow",
    )
    return {
        "status": WorkflowStatus.NOT_IMPLEMENTED.value,
        "errors": [message.model_dump(mode="json")],
    }
