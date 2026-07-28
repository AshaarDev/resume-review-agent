"""Resume Creator model boundary tests."""

from types import SimpleNamespace

import pytest

from core.creator_schemas import GeneratedResumeDocument, ResumeCreationBrief
from services import creator_service
from services.creator_service import CreatorServiceError
from services.resume_policy import get_resume_quality_policy


def _brief() -> ResumeCreationBrief:
    return ResumeCreationBrief(
        full_name="Ada Lovelace",
        target_role="Software Engineer",
        source_facts=[
            {
                "fact_id": "fact-1",
                "text": "Built a Python compiler prototype in 2025.",
            }
        ],
    )


def _document() -> GeneratedResumeDocument:
    return GeneratedResumeDocument(
        projects=[
            {
                "name": "Compiler prototype",
                "date_range": "2025",
                "source_fact_ids": ["fact-1"],
                "bullets": [
                    {
                        "text": "Built a Python compiler prototype.",
                        "source_fact_ids": ["fact-1"],
                    }
                ],
            }
        ]
    )


def test_creator_uses_configured_luna_structured_output(monkeypatch):
    calls = []

    class FakeResponses:
        def parse(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_parsed=_document())

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(creator_service, "get_creator_client", lambda: fake_client)
    monkeypatch.setattr(creator_service.settings, "CREATOR_MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(
        creator_service.settings, "CREATOR_REASONING_EFFORT", "none"
    )

    result = creator_service.generate_resume_document(
        _brief(), get_resume_quality_policy()
    )

    assert result.projects[0].name == "Compiler prototype"
    assert calls[0]["model"] == "gpt-5.6-luna"
    assert calls[0]["reasoning"] == {"effort": "none"}
    assert calls[0]["text_format"] is GeneratedResumeDocument


def test_creator_reports_missing_openai_configuration(monkeypatch):
    creator_service.reset_creator_client()
    monkeypatch.setattr(creator_service.settings, "OPENAI_API_KEY", "")

    with pytest.raises(CreatorServiceError) as exc_info:
        creator_service.get_creator_client()

    assert exc_info.value.code == "CREATOR_NOT_CONFIGURED"
