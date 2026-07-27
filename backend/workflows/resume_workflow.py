"""Resume workflow orchestration with LangGraph.

The graph is compiled ONCE at module import for performance.
"""

import logging
import uuid
from pathlib import Path

from langgraph.graph import END, StateGraph

from core.workflow_schemas import (
    AgentStatus,
    OrchestratorSummary,
    ReviewAgentResult,
    ResumeWorkflowResponse,
    WorkflowIntent,
    WorkflowStatus,
)
from services.document_processor import (
    normalize_file_type,
    resume_workspace,
    validate_resume_bytes,
)
from workflows.nodes.finalization_nodes import (
    finalize_workflow,
    synthesize_final_response,
)
from workflows.nodes.review_nodes import (
    not_implemented,
    run_review_agent,
    validate_intent,
)
from workflows.routing import route_by_intent
from workflows.state import ResumeWorkflowState

logger = logging.getLogger(__name__)


def _build_workflow_graph():
    """Build and compile the workflow graph.
    
    This function is called ONCE at module import time.
    """
    graph = StateGraph(ResumeWorkflowState)
    
    # Add nodes
    graph.add_node("validate_intent", validate_intent)
    graph.add_node("run_review_agent", run_review_agent)
    graph.add_node("not_implemented", not_implemented)
    graph.add_node("synthesize_final_response", synthesize_final_response)
    graph.add_node("finalize_workflow", finalize_workflow)
    
    # Set entry point
    graph.set_entry_point("validate_intent")
    
    # Add conditional routing after validation
    graph.add_conditional_edges(
        "validate_intent",
        route_by_intent,
        {
            "run_review_agent": "run_review_agent",
            "not_implemented": "not_implemented",
        }
    )
    
    # Review path: agent -> synthesis -> finalization -> end
    graph.add_edge("run_review_agent", "synthesize_final_response")
    graph.add_edge("synthesize_final_response", "finalize_workflow")
    graph.add_edge("finalize_workflow", END)
    
    # Not-implemented path: skip to finalization -> end
    graph.add_edge("not_implemented", "finalize_workflow")
    
    return graph.compile()


# Compile graph ONCE at module import
_compiled_workflow = _build_workflow_graph()
logger.info("Resume workflow graph compiled successfully")


def run_resume_review_workflow(
    file_bytes: bytes,
    file_type: str,
    job_description: str = "",
    user_instructions: str = "",
) -> ResumeWorkflowResponse:
    """Execute the resume review workflow.
    
    This is the main entry point called by FastAPI and MCP.
    
    Args:
        file_bytes: Resume file bytes
        file_type: File extension (pdf, docx, etc.)
        job_description: Optional job description
        user_instructions: Optional user instructions
        
    Returns:
        ResumeWorkflowResponse with complete results
    """
    # Generate workflow ID
    workflow_id = str(uuid.uuid4())
    
    # Validate and normalize file type
    normalized_type = normalize_file_type(file_type)
    validate_resume_bytes(file_bytes)
    
    # Create request workspace
    with resume_workspace() as workspace:
        # Save source document
        source_path = workspace.save_upload(file_bytes, normalized_type)
        
        # Initialize workflow state
        initial_state: ResumeWorkflowState = {
            "workflow_id": workflow_id,
            "intent": "review",  # Only review is supported in this phase
            "status": WorkflowStatus.PENDING.value,
            "source_path": str(source_path),
            "file_type": normalized_type,
            "job_description": job_description,
            "user_instructions": user_instructions,
            "review_result": None,
            "creation_result": None,
            "comparison_result": None,
            "agent_statuses": {},
            "warnings": [],
            "errors": [],
            "final_response": None,
        }
        
        # Invoke pre-compiled workflow graph
        try:
            final_state = _compiled_workflow.invoke(initial_state)
        except Exception as exc:
            logger.exception("Workflow execution failed")
            # Return error response
            return ResumeWorkflowResponse(
                workflow_id=workflow_id,
                intent=WorkflowIntent.REVIEW,
                status=WorkflowStatus.FAILED,
                final_message="Workflow execution failed. Please try again.",
                summary=OrchestratorSummary(
                    overall_assessment="Workflow failed to execute.",
                    top_strengths=[],
                    priority_actions=[],
                    next_step="Please try again.",
                ),
                review=ReviewAgentResult(
                    status=AgentStatus.FAILED,
                    content_review={"status": "unavailable"},
                    visual_review={"status": "unavailable"},
                    layout_analysis={"status": "unavailable"},
                    proposed_actions=[],
                    warnings=[],
                    errors=[str(exc)],
                ),
                agent_statuses={
                    "resume_review_agent": AgentStatus.FAILED,
                    "resume_creator_agent": AgentStatus.NOT_INVOKED,
                },
                warnings=[],
                errors=[f"Workflow execution failed: {str(exc)}"],
            )
        
        # Construct final response
        return _build_workflow_response(final_state)


def _build_workflow_response(state: ResumeWorkflowState) -> ResumeWorkflowResponse:
    """Build the final workflow response from state."""
    
    # Parse review result
    if state.get("review_result"):
        review = ReviewAgentResult.model_validate(state["review_result"])
    else:
        review = ReviewAgentResult(
            status=AgentStatus.FAILED,
            content_review={"status": "unavailable"},
            visual_review={"status": "unavailable"},
            layout_analysis={"status": "unavailable"},
            proposed_actions=[],
            warnings=[],
            errors=["No review result available"],
        )
    
    # Parse orchestrator summary
    if state.get("orchestrator_summary"):
        summary = OrchestratorSummary.model_validate(state["orchestrator_summary"])
    else:
        summary = OrchestratorSummary(
            overall_assessment="Review could not be completed.",
            top_strengths=[],
            priority_actions=[],
            next_step="Please try again.",
        )
    
    # Parse agent statuses
    agent_statuses = {
        k: AgentStatus(v) for k, v in state.get("agent_statuses", {}).items()
    }
    
    # Extract warnings and errors
    warnings = [w.get("message", "") for w in state.get("warnings", [])]
    errors = [e.get("message", "") for e in state.get("errors", [])]
    
    return ResumeWorkflowResponse(
        workflow_id=state["workflow_id"],
        intent=WorkflowIntent(state["intent"]),
        status=WorkflowStatus(state["status"]),
        final_message=state.get("final_message", ""),
        summary=summary,
        review=review,
        agent_statuses=agent_statuses,
        warnings=warnings,
        errors=errors,
    )
