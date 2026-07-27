"""Deterministic final message formatter - no model calls."""

from core.workflow_schemas import OrchestratorSummary, WorkflowStatus


def format_final_message(
    summary: OrchestratorSummary,
    workflow_status: WorkflowStatus,
    warnings: list[str],
) -> str:
    """Generate user-facing final message from orchestrator summary.
    
    This is a pure template-based formatter with NO model calls.
    Technical provider errors are kept in the warnings array, not in the message.
    
    Args:
        summary: Validated orchestrator summary
        workflow_status: Overall workflow status
        warnings: List of warning messages
        
    Returns:
        Formatted final message string
    """
    
    # Handle complete failure
    if workflow_status == WorkflowStatus.FAILED:
        return (
            "We were unable to complete your resume review. "
            "Please try again. If the issue persists, verify your file is a valid PDF or DOCX."
        )
    
    # Build message parts
    parts = []
    
    # Overall assessment
    parts.append(summary.overall_assessment)
    
    # Top strengths (if any)
    if summary.top_strengths:
        parts.append("")
        parts.append("Top strengths:")
        for strength in summary.top_strengths[:3]:
            parts.append(f"- {strength}")
    
    # Priority actions (if any)
    if summary.priority_actions:
        parts.append("")
        parts.append("Priority actions:")
        for i, action in enumerate(summary.priority_actions[:5], 1):
            parts.append(f"{i}. {action.title}: {action.recommendation}")
    
    # Next step
    parts.append("")
    parts.append(f"Next step: {summary.next_step}")
    
    return "\n".join(parts)
