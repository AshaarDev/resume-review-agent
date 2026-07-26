"""Request-scoped document conversion and page rendering."""

import base64
import binascii
import logging
import os
import shutil
import subprocess
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from core.config import settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEMP_ROOT = BACKEND_DIR / "temp"
SUPPORTED_FILE_TYPES = {"pdf", "docx", "jpg", "jpeg", "png"}


class DocumentProcessingError(RuntimeError):
    """A safe, categorized document-processing failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreparedDocument:
    """Files that stay valid for the lifetime of a resume workspace."""

    source_path: Path
    pdf_path: Optional[Path]
    page_image_paths: List[Path]
    page_count: int
    file_type: str


class ResumeWorkspace:
    """A unique per-request directory owned by the API workflow."""

    def __init__(self, path: Path):
        self.path = path

    def save_upload(self, file_bytes: bytes, file_type: str) -> Path:
        normalized_type = normalize_file_type(file_type)
        target = self.path / f"resume.{normalized_type}"
        target.write_bytes(file_bytes)
        return target


@contextmanager
def resume_workspace() -> Iterator[ResumeWorkspace]:
    """Keep intermediate files alive until every review branch is complete."""

    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    workspace_path = TEMP_ROOT / str(uuid.uuid4())
    workspace_path.mkdir()
    try:
        yield ResumeWorkspace(workspace_path)
    finally:
        try:
            shutil.rmtree(workspace_path)
        except OSError:
            logger.exception("Unable to clean resume workspace %s", workspace_path)


def normalize_file_type(file_type: str) -> str:
    """Normalize and validate a client-provided file extension."""

    normalized = file_type.strip().lower().lstrip(".")
    if normalized not in SUPPORTED_FILE_TYPES:
        raise DocumentProcessingError(
            "UNSUPPORTED_FILE_TYPE",
            "Supported resume formats are PDF, DOCX, JPG, JPEG, and PNG.",
        )
    return normalized


def decode_resume_file(file_base64: str) -> bytes:
    """Strictly decode an upload and enforce its size before disk or AI use."""

    compact_data = "".join(file_base64.split())
    estimated_size = (len(compact_data) * 3) // 4
    if estimated_size > settings.MAX_RESUME_FILE_BYTES + 2:
        raise DocumentProcessingError(
            "FILE_TOO_LARGE",
            f"Resume exceeds the {settings.MAX_RESUME_FILE_BYTES}-byte limit.",
        )
    try:
        file_bytes = base64.b64decode(compact_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise DocumentProcessingError(
            "INVALID_BASE64", "The uploaded resume is not valid base64 data."
        ) from exc
    validate_resume_bytes(file_bytes)
    return file_bytes


def validate_resume_bytes(file_bytes: bytes) -> None:
    """Enforce upload limits for non-base64 callers such as MCP tools."""

    if not file_bytes:
        raise DocumentProcessingError("EMPTY_FILE", "The uploaded resume is empty.")
    if len(file_bytes) > settings.MAX_RESUME_FILE_BYTES:
        raise DocumentProcessingError(
            "FILE_TOO_LARGE",
            f"Resume exceeds the {settings.MAX_RESUME_FILE_BYTES}-byte limit.",
        )


def _validate_render_dimensions(width: int, height: int, page_number: int) -> None:
    if (
        width > settings.MAX_VISION_IMAGE_DIMENSION
        or height > settings.MAX_VISION_IMAGE_DIMENSION
        or width * height > settings.MAX_VISION_IMAGE_PIXELS
    ):
        raise DocumentProcessingError(
            "IMAGE_RESOLUTION_LIMIT",
            f"Page {page_number} exceeds the configured image-resolution limit.",
        )


def render_pdf_pages(file_path: Path, temp_dir: Path) -> List[Path]:
    """Render validated PDF pages to local PNG files."""

    try:
        import fitz
    except ImportError as exc:
        raise DocumentProcessingError(
            "PDF_RENDERER_UNAVAILABLE", "PyMuPDF is required to render PDF resumes."
        ) from exc

    image_paths: List[Path] = []
    try:
        with fitz.open(file_path) as document:
            if document.page_count == 0:
                raise DocumentProcessingError(
                    "EMPTY_DOCUMENT", "The resume does not contain any pages."
                )
            if document.page_count > settings.MAX_RESUME_PAGES:
                raise DocumentProcessingError(
                    "PAGE_LIMIT_EXCEEDED",
                    f"Resume exceeds the {settings.MAX_RESUME_PAGES}-page limit.",
                )

            scale = settings.DOCUMENT_RENDER_DPI / 72
            matrix = fitz.Matrix(scale, scale)
            for page_index, page in enumerate(document):
                target_width = round(page.rect.width * scale)
                target_height = round(page.rect.height * scale)
                _validate_render_dimensions(
                    target_width, target_height, page_index + 1
                )
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = temp_dir / f"page_{page_index + 1}.png"
                pixmap.save(image_path)
                image_paths.append(image_path)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            "INVALID_PDF", "The PDF could not be opened or rendered."
        ) from exc
    return image_paths


def _convert_with_libreoffice(file_path: Path, temp_dir: Path) -> Optional[Path]:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        return None
    try:
        subprocess.run(
            [
                executable,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(file_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.DOCX_CONVERSION_TIMEOUT_SECONDS,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("LibreOffice DOCX conversion failed: %s", exc)
        return None
    output_path = temp_dir / f"{file_path.stem}.pdf"
    return output_path if output_path.is_file() else None


def _convert_with_docx2pdf(file_path: Path, temp_dir: Path) -> Optional[Path]:
    if os.name != "nt":
        return None
    try:
        from docx2pdf import convert
    except ImportError:
        return None

    output_path = temp_dir / f"{file_path.stem}.pdf"
    try:
        convert(str(file_path), str(output_path), keep_active=False)
    except Exception as exc:
        logger.warning("docx2pdf conversion failed: %s", exc)
        return None
    return output_path if output_path.is_file() else None


def convert_docx_to_pdf(file_path: Path, temp_dir: Path) -> Path:
    """Convert DOCX using the platform-appropriate available converter."""

    converters = (
        (_convert_with_docx2pdf, _convert_with_libreoffice)
        if os.name == "nt"
        else (_convert_with_libreoffice, _convert_with_docx2pdf)
    )
    for converter in converters:
        converted_path = converter(file_path, temp_dir)
        if converted_path is not None:
            return converted_path
    raise DocumentProcessingError(
        "DOCX_CONVERTER_UNAVAILABLE",
        "DOCX visual review requires Microsoft Word with docx2pdf on Windows "
        "or LibreOffice in the deployment environment.",
    )


def _prepare_image(file_path: Path, temp_dir: Path) -> List[Path]:
    try:
        from PIL import Image

        with Image.open(file_path) as image:
            image.load()
            _validate_render_dimensions(image.width, image.height, 1)
            output_path = temp_dir / "page_1.png"
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            image.save(output_path, format="PNG")
            return [output_path]
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            "INVALID_IMAGE", "The image could not be opened or rendered."
        ) from exc


def prepare_resume_for_vision(
    file_path: Path, file_type: str, temp_dir: Path
) -> PreparedDocument:
    """Prepare page images without taking ownership of workspace cleanup."""

    normalized_type = normalize_file_type(file_type)
    if normalized_type == "pdf":
        pdf_path = file_path
        page_images = render_pdf_pages(pdf_path, temp_dir)
    elif normalized_type == "docx":
        pdf_path = convert_docx_to_pdf(file_path, temp_dir)
        page_images = render_pdf_pages(pdf_path, temp_dir)
    else:
        pdf_path = None
        page_images = _prepare_image(file_path, temp_dir)

    return PreparedDocument(
        source_path=file_path,
        pdf_path=pdf_path,
        page_image_paths=page_images,
        page_count=len(page_images),
        file_type=normalized_type,
    )
