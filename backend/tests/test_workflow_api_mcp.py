"""Workflow transport compatibility and MCP registration tests."""

import asyncio
import base64
import json

from fastapi.testclient import TestClient

from core.workflow_schemas import (
    AgentStatus,
    ResumeWorkflowResponse,
    WorkflowIntent,
    WorkflowStatus,
)
from main import app
from mcp_server import resume_server
from routes import api

client = TestClient(app)


def _response() -> ResumeWorkflowResponse:
    return ResumeWorkflowResponse(
        workflow_id="test-id",
        intent=WorkflowIntent.REVIEW,
        status=WorkflowStatus.COMPLETED,
        final_message="Review complete.",
        agent_statuses={
            "resume_review_agent": AgentStatus.COMPLETED,
            "resume_creator_agent": AgentStatus.NOT_INVOKED,
        },
    )


def test_workflow_api_and_validation(monkeypatch):
    monkeypatch.setattr(api, "run_resume_workflow", lambda **kwargs: _response())
    response = client.post(
        "/api/resume-workflows",
        json={
            "intent": "review",
            "file_base64": base64.b64encode(b"pdf").decode(),
            "file_type": "pdf",
        },
    )
    assert response.status_code == 200
    assert response.json()["workflow_id"] == "test-id"

    missing = client.post(
        "/api/resume-workflows", json={"intent": "review"}
    )
    assert missing.status_code == 422


def test_create_intent_does_not_require_upload(monkeypatch):
    captured = {}

    def fake(**kwargs):
        captured.update(kwargs)
        response = _response()
        return response.model_copy(
            update={
                "intent": WorkflowIntent.CREATE,
                "status": WorkflowStatus.NOT_IMPLEMENTED,
            }
        )

    monkeypatch.setattr(api, "run_resume_workflow", fake)
    response = client.post(
        "/api/resume-workflows", json={"intent": "create"}
    )
    assert response.status_code == 200
    assert "file_bytes" not in captured


def test_all_thirteen_mcp_tools_are_unique():
    tools = asyncio.run(resume_server.mcp.list_tools())
    names = [tool.name for tool in tools]
    assert len(names) == len(set(names)) == 13
    assert "run_resume_review_workflow" in names
    assert "run_resume_review_workflow_base64" in names


def test_current_resume_policy_is_exposed_as_an_mcp_resource():
    resources = asyncio.run(resume_server.mcp.list_resources())
    uris = {str(resource.uri) for resource in resources}
    policy = json.loads(resume_server.get_resume_review_policy())

    assert "resume-policy://current" in uris
    assert policy["policy_id"] == "resume-review"
    assert policy["version"] == "1.0"


def test_legacy_path_tool_now_enforces_allowed_roots():
    result = resume_server.parse_resume(
        r"C:\Users\someone\private-resume.pdf"
    )
    assert result["error_code"] == "FILE_PATH_NOT_ALLOWED"
