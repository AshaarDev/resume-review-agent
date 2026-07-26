"""Tests for required deterministic layout measurements."""

from pathlib import Path

import fitz

from core.review_schemas import ReviewStatus
from services.document_processor import PreparedDocument
from services.layout_analyzer import analyze_layout


def test_pdf_layout_includes_dimensions_density_and_fonts(tmp_path: Path):
    pdf_path = tmp_path / "resume.pdf"
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "EXPERIENCE", fontsize=16)
    page.insert_text((72, 100), "Software Engineer", fontsize=10)
    document.save(pdf_path)
    document.close()

    prepared = PreparedDocument(
        source_path=pdf_path,
        pdf_path=pdf_path,
        page_image_paths=[],
        page_count=1,
        file_type="pdf",
    )
    result = analyze_layout(prepared)

    assert result.status == ReviewStatus.AVAILABLE
    assert result.page_count == 1
    assert result.pages[0].width_points == 612
    assert result.pages[0].height_points == 792
    assert result.pages[0].text_density > 0
    assert result.pages[0].font_sizes == [10.0, 16.0]
    assert result.pages[0].min_font_size == 10.0
    assert result.pages[0].max_font_size == 16.0
