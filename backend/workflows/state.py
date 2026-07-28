"""Internal LangGraph state; no checkpointer is used while paths are temporary."""

from typing import Literal, TypedDict


class ResumeWorkflowState(TypedDict, total=False):
    workflow_id: str
    policy: dict
    policy_id: str
    policy_version: str
    intent: Literal["review", "create", "revise"]
    status: str
    source_path: str
    workspace_path: str
    file_type: str
    job_description: str
    user_instructions: str
    review_result: dict | None
    creation_result: dict | None
    comparison_result: dict | None
    orchestrator_summary: dict | None
    agent_statuses: dict[str, str]
    warnings: list[dict]
    errors: list[dict]
    final_message: str
    final_response: dict | None
