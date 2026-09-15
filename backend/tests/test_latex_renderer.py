"""Approved template rendering and LaTeX safety tests."""

from core.creator_schemas import GeneratedResumeDocument, ResumeCreationBrief
from services.latex_renderer import latex_escape, render_resume_latex


def test_latex_escape_neutralizes_control_characters():
    escaped = latex_escape(r"R&D_50% $value {x} \input")
    assert escaped == (
        r"R\&D\_50\% \$value \{x\} \textbackslash{}input"
    )


def test_renderer_uses_template_and_selective_bold():
    brief = ResumeCreationBrief(
        full_name="Ada & Grace",
        email="ada@example.com",
        links=["https://example.com/profile"],
        source_facts=[{"fact_id": "f1", "text": "Saved 40%."}],
    )
    document = GeneratedResumeDocument(
        projects=[
            {
                "name": "Compiler",
                "date_range": "2025",
                "source_fact_ids": ["f1"],
                "bullets": [
                    {
                        "text": "Saved 40% of processing time.",
                        "bold_phrases": ["40%"],
                        "source_fact_ids": ["f1"],
                    }
                ],
            }
        ]
    )

    rendered = render_resume_latex(brief, document)

    assert r"\fontsize{22}{24}" in rendered and r"Ada \& Grace" in rendered
    assert r"\usepackage{mathpazo}" in rendered
    assert r"\fontsize{9.2}{10.6}" in rendered
    assert r"\textbf{40\%}" in rendered
    assert r"\section{PROJECTS}" in rendered
    assert "%%__PROJECTS__%%" not in rendered


def test_unsafe_link_is_not_rendered_as_href():
    brief = ResumeCreationBrief(
        full_name="Ada",
        links=[r"https://example.com/}{\input{secret}}"],
        source_facts=[{"fact_id": "f1", "text": "Built compiler."}],
    )
    document = GeneratedResumeDocument(
        skill_groups=[
            {
                "label": "Languages",
                "skills": ["Python"],
                "source_fact_ids": ["f1"],
            }
        ]
    )

    rendered = render_resume_latex(brief, document)
    assert r"\input{secret}" not in rendered
