"""Sanitized progress events emitted by long-running resume workflows."""

from typing import Any, Callable, Optional


WorkflowEventSink = Callable[[dict[str, Any]], None]


def emit_workflow_event(
    sink: Optional[WorkflowEventSink],
    *,
    phase: str,
    status: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Emit safe operational progress without exposing prompts or reasoning."""

    if sink is None:
        return
    event = {
        "phase": phase,
        "status": status,
        "message": message,
        "details": details or {},
    }
    try:
        sink(event)
    except Exception:
        # Client progress must never be able to break the actual workflow.
        return
