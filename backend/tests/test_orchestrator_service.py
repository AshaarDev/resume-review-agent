"""Responses API synthesis, early-exit, and fallback tests."""

from types import SimpleNamespace

from core.workflow_schemas import AgentStatus, ReviewAgentResult
from services import orchestrator_service


def _result(status=AgentStatus.COMPLETED) -> ReviewAgentResult:
    return ReviewAgentResult(
        status=status,
        policy_id="resume-review",
        policy_version="1.0",
        content_review={"status": "available", "response": "Strong content."},
        visual_review={
            "status": "available",
            "result": {
                "visual_score": 85,
                "pass_status": True,
                "strengths": ["Clear headings"],
                "issues": [],
            },
        },
        layout_analysis={"status": "available", "page_count": 1},
        proposed_actions=[
            {
                "priority": 1,
                "source": "visual",
                "issue_code": "CRITICAL_TEST",
                "title": "Critical action",
                "recommendation": "Fix it.",
            }
        ],
    )


def test_failed_review_skips_openai(monkeypatch):
    monkeypatch.setattr(
        orchestrator_service,
        "get_orchestrator_client",
        lambda: (_ for _ in ()).throw(AssertionError("must not be called")),
    )
    result = orchestrator_service.synthesize_review_response(
        _result(AgentStatus.FAILED), "", ""
    )
    assert result.warnings == []
    assert "could not be completed" in result.summary.overall_assessment


def test_responses_api_structured_output(monkeypatch):
    expected = orchestrator_service._deterministic_fallback_summary(_result())
    parse = lambda **kwargs: SimpleNamespace(output_parsed=expected)
    monkeypatch.setattr(
        orchestrator_service,
        "get_orchestrator_client",
        lambda: SimpleNamespace(
            responses=SimpleNamespace(parse=parse)
        ),
    )
    result = orchestrator_service.synthesize_review_response(
        _result(), "Engineer", "Keep it concise"
    )
    assert result.summary == expected
    assert result.warnings == []


def test_provider_failure_returns_review_based_fallback(monkeypatch):
    def fail(**kwargs):
        raise TimeoutError("secret provider detail")

    monkeypatch.setattr(
        orchestrator_service,
        "get_orchestrator_client",
        lambda: SimpleNamespace(
            responses=SimpleNamespace(parse=fail)
        ),
    )
    result = orchestrator_service.synthesize_review_response(
        _result(), "", ""
    )
    assert result.summary.priority_actions[0].issue_code == "CRITICAL_TEST"
    assert result.warnings[0].code == "ORCHESTRATOR_MODEL_UNAVAILABLE"
    assert "secret provider detail" not in result.warnings[0].message


def test_compacted_synthesis_input_is_valid_json():
    import json

    review = _result()
    review.content_review.response = "x" * 30000
    serialized = orchestrator_service._prepare_synthesis_input(
        review, "job", "instructions"
    )
    parsed = json.loads(serialized)
    assert parsed["review"]["proposed_actions"][0]["issue_code"] == "CRITICAL_TEST"
