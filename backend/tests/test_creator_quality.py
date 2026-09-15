"""Resume Creator deterministic policy and completeness checks."""

from core.creator_schemas import GeneratedResumeDocument, ResumeCreationBrief
from services.creator_quality import assess_creator_output
from services.resume_policy import get_resume_quality_policy


def _brief() -> ResumeCreationBrief:
    return ResumeCreationBrief(
        full_name="Ada Lovelace",
        source_facts=[
            {
                "fact_id": "f1",
                "text": "Reduced processing time by 40% using caching.",
            },
            {
                "fact_id": "f2",
                "text": "Saved 10 hours per week by automating reports.",
            },
        ],
    )


def test_complete_xyz_resume_passes_structured_quality_gate():
    document = GeneratedResumeDocument(
        professional_summary="Engineer who improves processing and automation.",
        professional_summary_source_fact_ids=["f1", "f2"],
        experiences=[
            {
                "organization": "Example Co",
                "role": "Engineer",
                "source_fact_ids": ["f1", "f2"],
                "bullets": [
                    {
                        "text": "Reduced processing time by 40% using caching.",
                        "bold_phrases": ["40%"],
                        "source_fact_ids": ["f1"],
                    },
                    {
                        "text": "Saved 10 hours per week by automating reports.",
                        "bold_phrases": ["10 hours"],
                        "source_fact_ids": ["f2"],
                    },
                    {
                        "text": "Improved job reliability by 25% through automated validation.",
                        "bold_phrases": ["25%"],
                        "source_fact_ids": ["f1"],
                        "is_mock": True,
                        "mock_reason": "Sample reliability outcome.",
                    },
                    {
                        "text": "Supported 5 stakeholders by building self-service dashboards.",
                        "bold_phrases": ["5 stakeholders"],
                        "source_fact_ids": ["f2"],
                        "is_mock": True,
                        "mock_reason": "Sample stakeholder scope.",
                    },
                ],
            }
        ],
    )

    report = assess_creator_output(
        _brief(), document, get_resume_quality_policy()
    )

    assert report.passed


def test_sparse_resume_returns_actionable_policy_feedback():
    document = GeneratedResumeDocument(
        projects=[
            {
                "name": "Automation",
                "source_fact_ids": ["f2"],
                "bullets": [
                    {
                        "text": "Worked on reports that saved 10 hours per week.",
                        "source_fact_ids": ["f2"],
                    }
                ],
            }
        ]
    )

    report = assess_creator_output(
        _brief(), document, get_resume_quality_policy()
    )

    assert not report.passed
    assert any("professional summary" in issue for issue in report.issues)
    assert any("XYZ-style" in issue for issue in report.issues)
    assert any("bold_phrases" in issue for issue in report.issues)


def test_quality_gate_rejects_dropped_user_source_fact():
    document = GeneratedResumeDocument(
        professional_summary="Engineer who improves processing systems.",
        professional_summary_source_fact_ids=["f1"],
        experiences=[
            {
                "organization": "Example Co",
                "role": "Engineer",
                "source_fact_ids": ["f1"],
                "bullets": [
                    {
                        "text": "Reduced processing time by 40% using caching.",
                        "bold_phrases": ["40%"],
                        "source_fact_ids": ["f1"],
                    }
                ],
            }
        ],
    )

    report = assess_creator_output(
        _brief(), document, get_resume_quality_policy()
    )

    assert any("f2" in issue and "source fact" in issue for issue in report.issues)
