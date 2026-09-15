"""Workflow transport compatibility and MCP registration tests."""

import asyncio
import base64
import json

import fitz
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
from services import artifact_store

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


def test_health_reports_pdf_runtime_status():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["latex_compiler_available"], bool)


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
        "/api/resume-workflows",
        json={
            "intent": "create",
            "creation_brief": {
                "full_name": "Ada Lovelace",
                "source_facts": [
                    {"fact_id": "fact-1", "text": "Built an engine."}
                ],
            },
        },
    )
    assert response.status_code == 200
    assert "file_bytes" not in captured


def test_workflow_sse_streams_real_progress_before_result(monkeypatch):
    def fake(event_sink=None, **kwargs):
        event_sink(
            {
                "phase": "pdf_compilation",
                "status": "completed",
                "message": "PDF compilation completed.",
                "details": {"pass": 1},
            }
        )
        return _response().model_copy(update={"intent": WorkflowIntent.CREATE})

    monkeypatch.setattr(api, "run_resume_workflow", fake)
    with client.stream(
        "POST",
        "/api/resume-workflows/stream",
        json={
            "intent": "create",
            "creation_brief": {
                "full_name": "Ada Lovelace",
                "source_facts": [
                    {"fact_id": "fact-1", "text": "Built an engine."}
                ],
            },
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: progress" in body
    assert '"phase":"pdf_compilation"' in body
    assert body.index("event: progress") < body.index("event: result")
    assert '"sequence":1' in body


def test_artifact_download_is_allowlisted(monkeypatch, tmp_path):
    artifact_id = "a" * 32
    artifact_dir = tmp_path / artifact_id
    artifact_dir.mkdir()
    (artifact_dir / "resume.tex").write_text("safe", encoding="utf-8")
    monkeypatch.setattr(artifact_store, "ARTIFACT_ROOT", tmp_path)

    response = client.get(f"/api/artifacts/{artifact_id}/resume.tex")
    blocked = client.get(f"/api/artifacts/{artifact_id}/../secret.txt")

    assert response.status_code == 200
    assert response.text == "safe"
    assert blocked.status_code == 404


def test_pdf_artifact_can_be_rendered_inline(monkeypatch, tmp_path):
    artifact_id = "b" * 32
    artifact_dir = tmp_path / artifact_id
    artifact_dir.mkdir()
    (artifact_dir / "resume.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(artifact_store, "ARTIFACT_ROOT", tmp_path)

    preview = client.get(
        f"/api/artifacts/{artifact_id}/resume.pdf?preview=true"
    )
    download = client.get(f"/api/artifacts/{artifact_id}/resume.pdf")

    assert preview.status_code == 200
    assert preview.headers["content-disposition"].startswith("inline;")
    assert download.headers["content-disposition"].startswith("attachment;")


def test_pdf_artifact_has_png_preview(monkeypatch, tmp_path):
    artifact_id = "c" * 32
    artifact_dir = tmp_path / artifact_id
    artifact_dir.mkdir()
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Resume preview")
    document.save(artifact_dir / "resume.pdf")
    document.close()
    monkeypatch.setattr(artifact_store, "ARTIFACT_ROOT", tmp_path)

    preview = client.get(f"/api/artifact-previews/{artifact_id}.png")

    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG")


def test_all_fourteen_mcp_tools_are_unique():
    tools = asyncio.run(resume_server.mcp.list_tools())
    names = [tool.name for tool in tools]
    assert len(names) == len(set(names)) == 14
    assert "run_resume_review_workflow" in names
    assert "run_resume_review_workflow_base64" in names
    assert "create_resume" in names


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
