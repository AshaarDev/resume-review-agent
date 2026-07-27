"""Workflow finalization nodes."""

import logging

from core.workflow_schemas import (
    AgentStatus,
    OrchestratorSummary,
    ReviewAgentResult,
    WorkflowStatus,
)
from services.message_formatter import format_final_message
from services.orchestrator_service import synthesize_review_response
from workflows.state import ResumeWorkflowState

logger = logging.getLogger(__name__)


def synthesize_final_response(state: ResumeWorkflowState) -> ResumeWorkflowState:
    """Call orchestrator service to synthesize final summary."""
    
    # Skip if review agent didn't run or failed completely
    if not state.get("review_result"):
        logger.warning("No review result available for synthesis")
        return state
    
    try:
        # Parse review result
        review_result = ReviewAgentResult.model_validate(state["review_result"])
        
        # Call orchestrator service (handles Luna or fallback)
        summary = synthesize_review_response(
            review_result=review_result,
            job_description=state["job_description"],
            user_instructions=state["user_instructions"],
        )
        
        # Store summary in state
        state["orchestrator_summary"] = summary.model_dump(mode="json")
        
    except Exception as exc:
        logger.exception("Orchestrator synthesis failed")
        state["warnings"].append({
            "source": "orchestrator",
            "code": "ORCHESTRATOR_SYNTHESIS_FAILED",
            "message": "Final synthesis failed; using deterministic summary."
        })
        
        # Create minimal fallback summary
        state["orchestrator_summary"] = OrchestratorSummary(
            overall_assessment="Resume review completed with limited synthesis.",
            top_strengths=[],
            priority_actions=[],
            next_step="Review the detailed findings below.",
        ).model_dump(mode="json")
    
    return state


def finalize_workflow(state: ResumeWorkflowState) -> ResumeWorkflowState:
    """Determine final workflow status and generate final message."""
    
    # Determine final workflow status
    if state.get("status") == WorkflowStatus.NOT_IMPLEMENTED.value:
        final_status = WorkflowStatus.NOT_IMPLEMENTED
    elif not state.get("review_result"):
        final_status = WorkflowStatus.FAILED
    else:
        review_result = ReviewAgentResult.model_validate(state["review_result"])
        
        if review_result.status == AgentStatus.COMPLETED:
            final_status = WorkflowStatus.COMPLETED
        elif review_result.status == AgentStatus.PARTIAL:
            final_status = WorkflowStatus.PARTIAL
        else:
            final_status = WorkflowStatus.FAILED
    
    state["status"] = final_status.value
    
    # Generate final message deterministically
    if state.get("orchestrator_summary"):
        summary = OrchestratorSummary.model_validate(state["orchestrator_summary"])
        warnings_list = [w.get("message", "") for w in state.get("warnings", [])]
        
        final_message = format_final_message(
            summary=summary,
            workflow_status=final_status,
            warnings=warnings_list,
        )
    else:
        # Fallback message if no summary
        final_message = "Resume review could not be completed. Please try again."
    
    state["final_message"] = final_message
    
    return state
