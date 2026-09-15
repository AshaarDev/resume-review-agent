"""LangGraph node for the Resume Creator Agent."""

import logging
from pathlib import Path

from agents.resume_creator_agent import ResumeCreatorAgent
from core.creator_schemas import ResumeCreationBrief
from core.policy_schemas import ResumeQualityPolicy
from core.workflow_schemas import AgentStatus, WorkflowMessage
from workflows.state import ResumeWorkflowState
from services.workflow_events import emit_workflow_event

logger = logging.getLogger(__name__)


def run_creator_agent(state: ResumeWorkflowState) -> dict:
    emit_workflow_event(
        state.get("event_sink"),
        phase="creator_agent",
        status="started",
        message="Resume Creator Agent started.",
    )
    try:
        arguments = dict(
            brief=ResumeCreationBrief.model_validate(state["creation_brief"]),
            job_description=state.get("job_description", ""),
            user_instructions=state.get("user_instructions", ""),
            workspace_path=Path(state["workspace_path"]),
            policy=ResumeQualityPolicy.model_validate(state["policy"]),
        )
        if state.get("event_sink") is not None:
            arguments["event_sink"] = state["event_sink"]
        result = ResumeCreatorAgent().run(**arguments)
        emit_workflow_event(
            state.get("event_sink"),
            phase="creator_agent",
            status=result.status,
            message="Resume Creator Agent returned its best validated draft.",
            details={
                "refinement_passes": result.refinement_passes,
                "page_count": result.final_page_count,
                "page_fill_ratio": result.page_fill_ratio,
            },
        )
        return {
            "creation_result": result.model_dump(mode="json"),
            "agent_statuses": {
                **state["agent_statuses"],
                "resume_creator_agent": result.status,
            },
            "warnings": [
                warning.model_dump(mode="json")
                for warning in result.warnings
            ],
            "errors": [
                error.model_dump(mode="json") for error in result.errors
            ],
        }
    except Exception:
        logger.exception("Creator Agent node failed")
        emit_workflow_event(
            state.get("event_sink"),
            phase="creator_agent",
            status="failed",
            message="Resume Creator Agent could not complete.",
        )
        error = WorkflowMessage(
            code="CREATOR_AGENT_FAILED",
            message="The Resume Creator Agent could not complete.",
            source="resume_creator_agent",
        )
        return {
            "agent_statuses": {
                **state["agent_statuses"],
                "resume_creator_agent": AgentStatus.FAILED.value,
            },
            "errors": [error.model_dump(mode="json")],
        }
