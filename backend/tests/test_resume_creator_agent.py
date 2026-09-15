"""Resume Creator Agent factual grounding and artifact behavior tests."""

from pathlib import Path

from agents import resume_creator_agent
from agents.resume_creator_agent import ResumeCreatorAgent
from core.creator_schemas import (
    CompilationStatus,
    GeneratedResumeDocument,
    ResumeCreationBrief,
)
from services.latex_compiler import LatexCompilationResult
from services.creator_quality import CreatorQualityReport
from services.resume_policy import get_resume_quality_policy


def _brief():
    return ResumeCreationBrief(
        full_name="Ada Lovelace",
        email="ada@example.com",
        source_facts=[
            {
                "fact_id": "work-1",
                "text": "Reduced processing time by 40% using caching.",
            }
        ],
    )


def _document(source_id="work-1"):
    return GeneratedResumeDocument(
        experiences=[
            {
                "organization": "Example Co",
                "role": "Engineer",
                "date_range": "2024 -- Present",
                "source_fact_ids": [source_id],
                "bullets": [
                    {
                        "text": "Reduced processing time by 40% using caching.",
                        "bold_phrases": ["40%"],
                        "source_fact_ids": [source_id],
                    }
                ],
            }
        ]
    )


def test_creator_builds_claim_ledger_and_source_artifact(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(
        resume_creator_agent, "generate_resume_document", lambda *args: _document()
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "compile_latex",
        lambda path: LatexCompilationResult(
            CompilationStatus.SOURCE_ONLY,
            error_code="LATEX_COMPILER_UNAVAILABLE",
            error_message="pdflatex unavailable",
        ),
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "save_resume_artifacts",
        lambda tex_path, pdf_path: "a" * 32,
    )

    result = ResumeCreatorAgent().run(
        _brief(), "", "", tmp_path, get_resume_quality_policy()
    )

    assert result.status == "partial"
    assert result.claims_ledger[0].source_fact_ids == ["work-1"]
    assert result.artifact.tex_download_url.endswith("/resume.tex")
    assert result.artifact.pdf_download_url is None
    rendered = (tmp_path / "resume.tex").read_text(encoding="utf-8")
    assert r"\textbf{40\%}" in rendered


def test_creator_rejects_unknown_source_fact(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        resume_creator_agent,
        "generate_resume_document",
        lambda *args: _document("invented-fact"),
    )

    result = ResumeCreatorAgent().run(
        _brief(), "", "", tmp_path, get_resume_quality_policy()
    )

    assert result.status == "failed"
    assert result.errors[0].code == "CREATOR_UNSUPPORTED_CLAIM"
    assert not (tmp_path / "resume.tex").exists()


def test_mock_bullet_is_identified_in_claim_ledger():
    document = _document()
    document.experiences[0].bullets[0].is_mock = True
    document.experiences[0].bullets[0].mock_reason = "Editable sample metric."

    claims = resume_creator_agent._build_and_validate_claims(_brief(), document)

    assert claims[0].is_mock is False
    assert claims[1].is_mock is True


def test_creator_recompiles_until_exact_one_page(monkeypatch, tmp_path: Path):
    initial = _document()
    revised = _document()
    revised.experiences[0].bullets.append(
        revised.experiences[0].bullets[0].model_copy(
            update={"text": "Improved reliability by 25% using monitoring."}
        )
    )
    generated = []
    refined = []
    events = []
    quality_reports = iter(
        [
            CreatorQualityReport(
                issues=["Condense to one page."],
                page_count=2,
                page_fill_ratio=0.95,
            ),
            CreatorQualityReport(
                issues=[], page_count=1, page_fill_ratio=0.82
            ),
        ]
    )

    monkeypatch.setattr(
        resume_creator_agent,
        "generate_resume_document",
        lambda *args: generated.append(True) or initial,
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "refine_resume_document",
        lambda *args: refined.append(args[3]) or revised,
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "compile_latex",
        lambda path: LatexCompilationResult(
            CompilationStatus.COMPILED,
            pdf_path=path.with_suffix(".pdf"),
        ),
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "assess_creator_output",
        lambda *args: next(quality_reports),
    )
    monkeypatch.setattr(
        resume_creator_agent,
        "save_resume_artifacts",
        lambda tex_path, pdf_path: "b" * 32,
    )
    monkeypatch.setattr(
        resume_creator_agent.settings, "CREATOR_MAX_REFINEMENT_PASSES", 3
    )

    result = ResumeCreatorAgent().run(
        _brief(), "", "", tmp_path, get_resume_quality_policy(), events.append
    )

    assert generated == [True]
    assert len(refined) == 1
    assert "HARD PAGE CONSTRAINT" in refined[0][0]
    assert result.status == "completed"
    assert result.refinement_passes == 1
    assert result.final_page_count == 1
    assert result.page_fill_ratio == 0.82
    assert any(event["phase"] == "refinement" for event in events)
    assert any(
        event["phase"] == "compiled_pdf_review"
        and event["details"]["page_count"] == 2
        for event in events
    )
