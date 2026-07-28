"""Restricted, timeout-bound LaTeX compilation for generated resumes."""

import shutil
import subprocess
from pathlib import Path

from core.config import settings
from core.creator_schemas import CompilationStatus


class LatexCompilationResult:
    def __init__(
        self,
        status: CompilationStatus,
        pdf_path: Path | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ):
        self.status = status
        self.pdf_path = pdf_path
        self.error_code = error_code
        self.error_message = error_message


def compile_latex(tex_path: Path) -> LatexCompilationResult:
    executable = shutil.which("pdflatex")
    if not executable:
        return LatexCompilationResult(
            CompilationStatus.SOURCE_ONLY,
            error_code="LATEX_COMPILER_UNAVAILABLE",
            error_message=(
                "The LaTeX source was created, but pdflatex is not installed."
            ),
        )
    try:
        completed = subprocess.run(
            [
                executable,
                "-no-shell-escape",
                "-interaction=nonstopmode",
                "-halt-on-error",
                tex_path.name,
            ],
            cwd=tex_path.parent,
            capture_output=True,
            text=True,
            timeout=settings.LATEX_COMPILE_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return LatexCompilationResult(
            CompilationStatus.FAILED,
            error_code="LATEX_COMPILE_TIMEOUT",
            error_message="The generated resume took too long to compile.",
        )
    except OSError:
        return LatexCompilationResult(
            CompilationStatus.FAILED,
            error_code="LATEX_COMPILE_FAILED",
            error_message="The generated resume could not be compiled.",
        )
    pdf_path = tex_path.with_suffix(".pdf")
    if completed.returncode != 0 or not pdf_path.exists():
        return LatexCompilationResult(
            CompilationStatus.FAILED,
            error_code="LATEX_COMPILE_FAILED",
            error_message="The generated LaTeX did not compile successfully.",
        )
    return LatexCompilationResult(CompilationStatus.COMPILED, pdf_path=pdf_path)
