"""Document preparation, safety-limit, and workspace-lifecycle tests."""

import base64
from pathlib import Path

import fitz
import pytest

from core.config import settings
from services import document_processor
from services.document_processor import (
    DocumentProcessingError,
    decode_resume_file,
    prepare_resume_for_vision,
    render_pdf_pages,
    resume_workspace,
)


def _create_pdf(path: Path, page_count: int = 1) -> None:
    document = fitz.open()
    for index in range(page_count):
        page = document.new_page()
        page.insert_text((72, 72), f"Resume page {index + 1}")
    document.save(path)
    document.close()


def test_workspace_is_cleaned_after_success(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    with resume_workspace() as workspace:
        workspace_path = workspace.path
        (workspace_path / "intermediate.txt").write_text("test")
        assert workspace_path.exists()
    assert not workspace_path.exists()


def test_workspace_is_cleaned_after_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(document_processor, "TEMP_ROOT", tmp_path)
    with pytest.raises(RuntimeError):
        with resume_workspace() as workspace:
            workspace_path = workspace.path
            raise RuntimeError("branch failed")
    assert not workspace_path.exists()


def test_decode_resume_enforces_file_size(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESUME_FILE_BYTES", 3)
    with pytest.raises(DocumentProcessingError) as exc_info:
        decode_resume_file(base64.b64encode(b"four").decode())
    assert exc_info.value.code == "FILE_TOO_LARGE"


def test_render_pdf_pages_and_enforce_page_limit(monkeypatch, tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    _create_pdf(pdf_path, page_count=2)

    monkeypatch.setattr(settings, "MAX_RESUME_PAGES", 2)
    images = render_pdf_pages(pdf_path, tmp_path)
    assert [path.name for path in images] == ["page_1.png", "page_2.png"]
    assert all(path.is_file() for path in images)

    monkeypatch.setattr(settings, "MAX_RESUME_PAGES", 1)
    with pytest.raises(DocumentProcessingError) as exc_info:
        render_pdf_pages(pdf_path, tmp_path)
    assert exc_info.value.code == "PAGE_LIMIT_EXCEEDED"


def test_prepare_pdf_keeps_paths_in_caller_workspace(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    _create_pdf(pdf_path)
    prepared = prepare_resume_for_vision(pdf_path, "pdf", tmp_path)
    assert prepared.page_count == 1
    assert prepared.pdf_path == pdf_path
    assert prepared.page_image_paths[0].exists()


def test_docx_conversion_falls_back_to_second_converter(monkeypatch, tmp_path):
    source = tmp_path / "resume.docx"
    source.write_bytes(b"docx")
    converted = tmp_path / "resume.pdf"
    calls = []

    def first_converter(file_path, temp_dir):
        calls.append("first")
        return None

    def second_converter(file_path, temp_dir):
        calls.append("second")
        converted.write_bytes(b"pdf")
        return converted

    if document_processor.os.name == "nt":
        monkeypatch.setattr(
            document_processor, "_convert_with_docx2pdf", first_converter
        )
        monkeypatch.setattr(
            document_processor, "_convert_with_libreoffice", second_converter
        )
    else:
        monkeypatch.setattr(
            document_processor, "_convert_with_libreoffice", first_converter
        )
        monkeypatch.setattr(
            document_processor, "_convert_with_docx2pdf", second_converter
        )

    result = document_processor.convert_docx_to_pdf(source, tmp_path)
    assert result == converted
    assert calls == ["first", "second"]


def test_corrupt_pdf_returns_safe_error(tmp_path):
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a pdf")
    with pytest.raises(DocumentProcessingError) as exc_info:
        render_pdf_pages(pdf_path, tmp_path)
    assert exc_info.value.code == "INVALID_PDF"
