"""Deterministic page dimensions, text-density, and font-size analysis."""

from collections import Counter
from pathlib import Path
from statistics import median
from typing import Iterable, List

from core.review_schemas import (
    LayoutAnalysisResponse,
    LayoutPageMetrics,
    ReviewStatus,
)
from services.document_processor import DocumentProcessingError, PreparedDocument


def _summarize_font_sizes(font_sizes: Iterable[float]) -> dict:
    rounded = [round(float(size), 1) for size in font_sizes if size > 0]
    if not rounded:
        return {
            "font_sizes": [],
            "min_font_size": None,
            "max_font_size": None,
            "median_font_size": None,
            "dominant_font_size": None,
        }
    counts = Counter(rounded)
    return {
        "font_sizes": sorted(set(rounded)),
        "min_font_size": min(rounded),
        "max_font_size": max(rounded),
        "median_font_size": round(float(median(rounded)), 1),
        "dominant_font_size": counts.most_common(1)[0][0],
    }


def _analyze_pdf(pdf_path: Path) -> LayoutAnalysisResponse:
    try:
        import fitz
    except ImportError as exc:
        raise DocumentProcessingError(
            "LAYOUT_ANALYZER_UNAVAILABLE",
            "PyMuPDF is required for deterministic layout analysis.",
        ) from exc

    pages: List[LayoutPageMetrics] = []
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_area = max(float(page.rect.width * page.rect.height), 1.0)
            occupied_area = 0.0
            font_sizes: List[float] = []
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
                occupied_area += max(0.0, x1 - x0) * max(0.0, y1 - y0)
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        size = span.get("size")
                        if size:
                            font_sizes.append(float(size))

            pages.append(
                LayoutPageMetrics(
                    page_number=page_index + 1,
                    width_points=float(page.rect.width),
                    height_points=float(page.rect.height),
                    text_density=min(occupied_area / page_area, 1.0),
                    **_summarize_font_sizes(font_sizes),
                )
            )
    return LayoutAnalysisResponse(
        status=ReviewStatus.AVAILABLE,
        page_count=len(pages),
        pages=pages,
    )


def _analyze_image(image_path: Path) -> LayoutAnalysisResponse:
    from PIL import Image

    with Image.open(image_path) as image:
        page = LayoutPageMetrics(
            page_number=1,
            width_points=float(image.width),
            height_points=float(image.height),
            text_density=0.0,
            font_sizes=[],
        )
    return LayoutAnalysisResponse(
        status=ReviewStatus.AVAILABLE, page_count=1, pages=[page]
    )


def analyze_layout(prepared: PreparedDocument) -> LayoutAnalysisResponse:
    """Analyze every prepared resume; this is required, not an optional flag."""

    try:
        if prepared.pdf_path is not None:
            return _analyze_pdf(prepared.pdf_path)
        return _analyze_image(prepared.page_image_paths[0])
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            "LAYOUT_ANALYSIS_FAILED",
            "Deterministic layout analysis could not be completed.",
        ) from exc
