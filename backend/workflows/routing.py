"""Workflow routing logic."""

from workflows.state import ResumeWorkflowState


def route_by_intent(state: ResumeWorkflowState) -> str:
    """Route workflow based on intent.
    
    Returns:
        Next node name to execute
    """
    intent = state["intent"]
    
    if intent == "review":
        return "run_review_agent"
    elif intent in ("create", "revise"):
        return "not_implemented"
    else:
        # Default to not_implemented for unknown intents
        return "not_implemented"
