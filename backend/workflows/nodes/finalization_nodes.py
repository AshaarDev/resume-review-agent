"""Synthesis and deterministic finalization nodes."""

from core.workflow_schemas import (
    AgentStatus,
    OrchestratorSummary,
    ReviewAgentResult,
    WorkflowMessage,
    WorkflowStatus,
)
from services.message_formatter import format_final_message
from services.orchestrator_service import synthesize_review_response
from workflows.state import ResumeWorkflowState


def synthesize_final_response(state: ResumeWorkflowState) -> dict:
    if not state.get("review_result"):
        return {}
    review = ReviewAgentResult.model_validate(state["review_result"])
    synthesis = synthesize_review_response(
        review,
        state.get("job_description", ""),
        state.get("user_instructions", ""),
    )
    warnings = [
        WorkflowMessage.model_validate(item)
        for item in state.get("warnings", [])
    ] + synthesis.warnings
    return {
        "orchestrator_summary": synthesis.summary.model_dump(mode="json"),
        "warnings": [
            warning.model_dump(mode="json") for warning in warnings
        ],
    }


def finalize_workflow(state: ResumeWorkflowState) -> dict:
    if state.get("status") == WorkflowStatus.NOT_IMPLEMENTED.value:
        status = WorkflowStatus.NOT_IMPLEMENTED
        return {
            "status": status.value,
            "final_message": (
                "This workflow is reserved for the future Resume Creator Agent "
                "and is not implemented yet."
            ),
        }

    review = (
        ReviewAgentResult.model_validate(state["review_result"])
        if state.get("review_result")
        else None
    )
    if review is None or review.status == AgentStatus.FAILED:
        status = WorkflowStatus.FAILED
    elif review.status == AgentStatus.PARTIAL:
        status = WorkflowStatus.PARTIAL
    else:
        status = WorkflowStatus.COMPLETED

    summary = (
        OrchestratorSummary.model_validate(state["orchestrator_summary"])
        if state.get("orchestrator_summary")
        else OrchestratorSummary(
            overall_assessment="The resume review could not be completed.",
            next_step="Verify the document and try again.",
        )
    )
    return {
        "status": status.value,
        "final_message": format_final_message(
            summary,
            status,
            [
                WorkflowMessage.model_validate(item)
                for item in state.get("warnings", [])
            ],
        ),
    }
