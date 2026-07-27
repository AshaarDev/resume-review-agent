"""Workflow state definition for LangGraph."""

from typing import Literal, TypedDict


class ResumeWorkflowState(TypedDict):
    """State passed through the LangGraph workflow.
    
    Note: This state contains temporary file paths and cannot be persisted
    until we implement durable artifact storage. Checkpointing is disabled
    for this phase.
    """

    workflow_id: str
    intent: Literal["review", "create", "revise"]
    status: str

    # Temporary paths - not suitable for persistence
    source_path: str
    file_type: str
    job_description: str
    user_instructions: str

    # Agent results
    review_result: dict | None
    creation_result: dict | None  # Reserved for future Creator Agent
    comparison_result: dict | None  # Reserved for future revision workflows

    # Execution tracking
    agent_statuses: dict[str, str]
    warnings: list[dict]
    errors: list[dict]

    # Final output
    final_response: dict | None
