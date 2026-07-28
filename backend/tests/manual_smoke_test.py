"""Optional real-provider workflow smoke test."""

import os

import fitz
import pytest

from core.workflow_schemas import WorkflowStatus
from workflows.resume_workflow import run_resume_review_workflow


@pytest.mark.manual
@pytest.mark.skipif(
    not os.getenv("RUN_MANUAL_TESTS"), reason="Manual provider test"
)
def test_full_workflow_with_real_apis():
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Jane Candidate\nSoftware Engineer\nExperience building Python APIs.",
        fontsize=11,
    )
    file_bytes = document.tobytes()
    document.close()

    response = run_resume_review_workflow(
        file_bytes,
        "pdf",
        job_description="Backend software engineer",
        user_instructions="Prioritize the most actionable improvements.",
    )
    assert response.status in {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.PARTIAL,
    }
    assert response.review is not None
    assert response.summary is not None
