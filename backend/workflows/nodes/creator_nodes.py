"""LangGraph node for the Resume Creator Agent."""

import logging
from pathlib import Path

from agents.resume_creator_agent import ResumeCreatorAgent
from core.creator_schemas import ResumeCreationBrief
from core.policy_schemas import ResumeQualityPolicy
from core.workflow_schemas import AgentStatus, WorkflowMessage
from workflows.state import ResumeWorkflowState

logger = logging.getLogger(__name__)


def run_creator_agent(state: ResumeWorkflowState) -> dict:
    try:
        result = ResumeCreatorAgent().run(
            brief=ResumeCreationBrief.model_validate(state["creation_brief"]),
            job_description=state.get("job_description", ""),
            user_instructions=state.get("user_instructions", ""),
            workspace_path=Path(state["workspace_path"]),
            policy=ResumeQualityPolicy.model_validate(state["policy"]),
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
