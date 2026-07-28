"""Top-level resume workflow coordinated by one precompiled LangGraph."""

import logging
import uuid
from typing import Optional

from langgraph.graph import END, START, StateGraph

from core.workflow_schemas import (
    AgentStatus,
    OrchestratorSummary,
    ResumeWorkflowResponse,
    ReviewAgentResult,
    WorkflowIntent,
    WorkflowMessage,
    WorkflowStatus,
)
from services.document_processor import (
    normalize_file_type,
    resume_workspace,
    validate_resume_bytes,
)
from services.resume_policy import get_resume_quality_policy
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
    graph = StateGraph(ResumeWorkflowState)
    graph.add_node("validate_intent", validate_intent)
    graph.add_node("run_review_agent", run_review_agent)
    graph.add_node("not_implemented", not_implemented)
    graph.add_node("synthesize_final_response", synthesize_final_response)
    graph.add_node("finalize_workflow", finalize_workflow)
    graph.add_edge(START, "validate_intent")
    graph.add_conditional_edges(
        "validate_intent",
        route_by_intent,
        {
            "run_review_agent": "run_review_agent",
            "not_implemented": "not_implemented",
        },
    )
    graph.add_edge("run_review_agent", "synthesize_final_response")
    graph.add_edge("synthesize_final_response", "finalize_workflow")
    graph.add_edge("not_implemented", "finalize_workflow")
    graph.add_edge("finalize_workflow", END)
    return graph.compile()


_compiled_workflow = _build_workflow_graph()


def run_resume_workflow(
    intent: WorkflowIntent,
    file_bytes: Optional[bytes] = None,
    file_type: Optional[str] = None,
    job_description: str = "",
    user_instructions: str = "",
) -> ResumeWorkflowResponse:
    """Run an intent through the shared graph and own all temporary artifacts."""

    workflow_id = str(uuid.uuid4())
    if intent != WorkflowIntent.REVIEW:
        state = _initial_state(
            workflow_id, intent, "", "", "", job_description, user_instructions
        )
        return _build_workflow_response(_compiled_workflow.invoke(state))

    if file_bytes is None or file_type is None:
        raise ValueError("Review workflows require file bytes and a file type")
    normalized_type = normalize_file_type(file_type)
    validate_resume_bytes(file_bytes)
    with resume_workspace() as workspace:
        source_path = workspace.save_upload(file_bytes, normalized_type)
        state = _initial_state(
            workflow_id,
            intent,
            str(source_path),
            str(workspace.path),
            normalized_type,
            job_description,
            user_instructions,
        )
        try:
            final_state = _compiled_workflow.invoke(state)
        except Exception:
            logger.exception("Resume workflow execution failed")
            return _failed_response(workflow_id, intent)
        return _build_workflow_response(final_state)


def run_resume_review_workflow(
    file_bytes: bytes,
    file_type: str,
    job_description: str = "",
    user_instructions: str = "",
) -> ResumeWorkflowResponse:
    """Backward-compatible review-specific workflow entrypoint."""

    return run_resume_workflow(
        WorkflowIntent.REVIEW,
        file_bytes,
        file_type,
        job_description,
        user_instructions,
    )


def _initial_state(
    workflow_id: str,
    intent: WorkflowIntent,
    source_path: str,
    workspace_path: str,
    file_type: str,
    job_description: str,
    user_instructions: str,
) -> ResumeWorkflowState:
    policy = get_resume_quality_policy()
    return {
        "workflow_id": workflow_id,
        "policy": policy.model_dump(mode="json"),
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "intent": intent.value,
        "status": WorkflowStatus.PENDING.value,
        "source_path": source_path,
        "workspace_path": workspace_path,
        "file_type": file_type,
        "job_description": job_description,
        "user_instructions": user_instructions,
        "review_result": None,
        "creation_result": None,
        "comparison_result": None,
        "orchestrator_summary": None,
        "agent_statuses": {},
        "warnings": [],
        "errors": [],
        "final_response": None,
    }


def _build_workflow_response(
    state: ResumeWorkflowState,
) -> ResumeWorkflowResponse:
    return ResumeWorkflowResponse(
        workflow_id=state["workflow_id"],
        policy_id=state.get("policy_id"),
        policy_version=state.get("policy_version"),
        intent=WorkflowIntent(state["intent"]),
        status=WorkflowStatus(state["status"]),
        final_message=state.get("final_message", ""),
        summary=(
            OrchestratorSummary.model_validate(state["orchestrator_summary"])
            if state.get("orchestrator_summary")
            else None
        ),
        review=(
            ReviewAgentResult.model_validate(state["review_result"])
            if state.get("review_result")
            else None
        ),
        agent_statuses={
            name: AgentStatus(value)
            for name, value in state.get("agent_statuses", {}).items()
        },
        warnings=[
            WorkflowMessage.model_validate(item)
            for item in state.get("warnings", [])
        ],
        errors=[
            WorkflowMessage.model_validate(item)
            for item in state.get("errors", [])
        ],
    )


def _failed_response(
    workflow_id: str, intent: WorkflowIntent
) -> ResumeWorkflowResponse:
    error = WorkflowMessage(
        code="WORKFLOW_EXECUTION_FAILED",
        message="The workflow could not complete. Please try again.",
        source="workflow",
    )
    return ResumeWorkflowResponse(
        workflow_id=workflow_id,
        policy_id=get_resume_quality_policy().policy_id,
        policy_version=get_resume_quality_policy().version,
        intent=intent,
        status=WorkflowStatus.FAILED,
        final_message=error.message,
        summary=None,
        review=None,
        agent_statuses={
            "resume_review_agent": AgentStatus.FAILED,
            "resume_creator_agent": AgentStatus.NOT_INVOKED,
        },
        errors=[error],
    )
