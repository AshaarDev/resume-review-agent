"""Security tests for local path inputs accepted by MCP review tools."""

from pathlib import Path

import pytest

from core.config import settings
from services.document_processor import DocumentProcessingError
from services.review_pipeline import load_resume_file


def test_mcp_file_inside_approved_root_is_allowed(monkeypatch, tmp_path: Path):
    approved_root = tmp_path / "uploads"
    approved_root.mkdir()
    resume_path = approved_root / "resume.pdf"
    resume_path.write_bytes(b"resume")
    monkeypatch.setattr(
        settings, "MCP_ALLOWED_FILE_ROOTS", str(approved_root)
    )

    file_bytes, file_type = load_resume_file(str(resume_path))

    assert file_bytes == b"resume"
    assert file_type == "pdf"


def test_arbitrary_machine_path_is_rejected(monkeypatch, tmp_path: Path):
    approved_root = tmp_path / "uploads"
    approved_root.mkdir()
    private_path = tmp_path / "private-file.pdf"
    private_path.write_bytes(b"private")
    monkeypatch.setattr(
        settings, "MCP_ALLOWED_FILE_ROOTS", str(approved_root)
    )

    with pytest.raises(DocumentProcessingError) as exc_info:
        load_resume_file(str(private_path))

    assert exc_info.value.code == "FILE_PATH_NOT_ALLOWED"


def test_parent_traversal_cannot_escape_approved_root(
    monkeypatch, tmp_path: Path
):
    approved_root = tmp_path / "uploads"
    approved_root.mkdir()
    outside_path = tmp_path / "outside.pdf"
    outside_path.write_bytes(b"outside")
    traversal_path = approved_root / ".." / "outside.pdf"
    monkeypatch.setattr(
        settings, "MCP_ALLOWED_FILE_ROOTS", str(approved_root)
    )

    with pytest.raises(DocumentProcessingError) as exc_info:
        load_resume_file(str(traversal_path))

    assert exc_info.value.code == "FILE_PATH_NOT_ALLOWED"


def test_empty_approved_root_configuration_disables_path_tools(
    monkeypatch, tmp_path: Path
):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"resume")
    monkeypatch.setattr(settings, "MCP_ALLOWED_FILE_ROOTS", "")

    with pytest.raises(DocumentProcessingError) as exc_info:
        load_resume_file(str(resume_path))

    assert exc_info.value.code == "MCP_FILE_ROOTS_NOT_CONFIGURED"
