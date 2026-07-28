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
