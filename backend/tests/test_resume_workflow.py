"""Graph routing, workflow status, and workspace lifecycle tests."""

from pathlib import Path

from agents.resume_review_agent import ResumeReviewAgent
from agents.resume_creator_agent import ResumeCreatorAgent
from core.creator_schemas import CreatorAgentResult, ResumeCreationBrief
from core.workflow_schemas import (
    AgentStatus,
    ReviewAgentResult,
    WorkflowIntent,
    WorkflowStatus,
)
from services import document_processor, orchestrator_service
from workflows.resume_workflow import run_resume_workflow


def _agent_result() -> ReviewAgentResult:
    return ReviewAgentResult(
        status=AgentStatus.COMPLETED,
        policy_id="resume-review",
        policy_version="1.0",
        content_review={"status": "available", "response": "Good."},
        visual_review={
            "status": "available",
            "result": {
                "visual_score": 90,
                "pass_status": True,
                "strengths": [],
                "issues": [],
            },
        },
        layout_analysis={"status": "available", "page_count": 1},
    )


def _creation_brief() -> ResumeCreationBrief:
    return ResumeCreationBrief(
        full_name="Ada Lovelace",
        source_facts=[
            {"fact_id": "work-1", "text": "Built an analytics engine."}
        ],
    )


def test_revise_is_reserved_without_agent_calls(monkeypatch):
    monkeypatch.setattr(
        ResumeReviewAgent,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("agent must not run")
        ),
    )
    response = run_resume_workflow(WorkflowIntent.REVISE)
    assert response.status == WorkflowStatus.NOT_IMPLEMENTED
    assert response.review is None
    assert (
        response.agent_statuses["resume_creator_agent"]
        == AgentStatus.NOT_INVOKED
    )


def test_create_routes_to_creator_and_cleans_workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    observed = {}

    def fake_run(
        self,
        brief,
        job_description,
        user_instructions,
        workspace_path,
        policy,
    ):
        observed["brief"] = brief
        observed["workspace"] = workspace_path
        return CreatorAgentResult(
            status="partial",
            model="gpt-5.6-luna",
            policy_id=policy.policy_id,
            policy_version=policy.version,
        )

    monkeypatch.setattr(ResumeCreatorAgent, "run", fake_run)
    response = run_resume_workflow(
        WorkflowIntent.CREATE, creation_brief=_creation_brief()
    )

    assert response.status == WorkflowStatus.PARTIAL
    assert response.creation is not None
    assert observed["brief"].full_name == "Ada Lovelace"
    assert list(tmp_path.iterdir()) == []


def test_review_uses_one_workspace_and_cleans_it(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    observed = {}

    def fake_run(self, source_path, file_type, job_description,
                 user_instructions, workspace_path, policy=None):
        observed["source_parent"] = source_path.parent
        observed["workspace"] = workspace_path
        return _agent_result()

    monkeypatch.setattr(ResumeReviewAgent, "run", fake_run)
    monkeypatch.setattr(
        orchestrator_service,
        "get_orchestrator_client",
        lambda: (_ for _ in ()).throw(TimeoutError()),
    )
    response = run_resume_workflow(
        WorkflowIntent.REVIEW, b"not-a-real-pdf", "pdf"
    )

    assert response.status == WorkflowStatus.COMPLETED
    assert observed["source_parent"] == observed["workspace"]
    assert list(tmp_path.iterdir()) == []
    assert response.warnings[0].code == "ORCHESTRATOR_MODEL_UNAVAILABLE"
    serialized = response.model_dump_json()
    assert str(tmp_path) not in serialized
    assert "not-a-real-pdf" not in serialized
