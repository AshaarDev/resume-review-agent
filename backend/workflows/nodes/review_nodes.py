"""Review workflow nodes."""

import logging
from pathlib import Path

from agents.resume_review_agent import ResumeReviewAgent
from core.workflow_schemas import AgentStatus, WorkflowStatus
from workflows.state import ResumeWorkflowState

logger = logging.getLogger(__name__)


def validate_intent(state: ResumeWorkflowState) -> ResumeWorkflowState:
    """Validate the workflow intent and initialize agent statuses."""
    
    state["status"] = WorkflowStatus.RUNNING.value
    state["agent_statuses"] = {
        "resume_review_agent": AgentStatus.PENDING.value,
        "resume_creator_agent": AgentStatus.NOT_INVOKED.value,
    }
    state["warnings"] = []
    state["errors"] = []
    
    return state


def run_review_agent(state: ResumeWorkflowState) -> ResumeWorkflowState:
    """Execute the Resume Review Agent."""
    
    # Update agent status
    state["agent_statuses"]["resume_review_agent"] = AgentStatus.RUNNING.value
    
    try:
        # Instantiate and run the agent
        agent = ResumeReviewAgent()
        result = agent.run(
            source_path=Path(state["source_path"]),
            file_type=state["file_type"],
            job_description=state["job_description"],
            user_instructions=state["user_instructions"],
            workspace_path=Path(state["source_path"]).parent,
        )
        
        # Store result
        state["review_result"] = result.model_dump(mode="json")
        state["agent_statuses"]["resume_review_agent"] = result.status.value
        
        # Collect warnings
        for warning in result.warnings:
            state["warnings"].append({"source": "review_agent", "message": warning})
        
        # Collect errors
        for error in result.errors:
            state["errors"].append({"source": "review_agent", "message": error})
        
    except Exception as exc:
        logger.exception("Review agent execution failed")
        state["agent_statuses"]["resume_review_agent"] = AgentStatus.FAILED.value
        state["errors"].append({
            "source": "review_agent",
            "message": f"Agent execution failed: {str(exc)}"
        })
    
    return state


def not_implemented(state: ResumeWorkflowState) -> ResumeWorkflowState:
    """Handle not-implemented workflow intents (create, revise)."""
    
    state["status"] = WorkflowStatus.NOT_IMPLEMENTED.value
    state["errors"].append({
        "source": "workflow",
        "message": f"The '{state['intent']}' workflow is not yet implemented."
    })
    
    return state
