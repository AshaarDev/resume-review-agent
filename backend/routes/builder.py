"""User-authored resumes: shared template and isolated rendering, no AI."""

from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from core.builder_schemas import BuilderDraft
from services.resume_builder import render_builder_latex
from services.word_renderer import render_builder_word
from services.latex_compiler import compile_latex
from services.artifact_store import save_resume_artifacts

router = APIRouter(prefix="/api/resume-builder", tags=["resume-builder"])


def _compile(draft: BuilderDraft, directory: str):
    try:
        latex = render_builder_latex(draft)
    except ValueError as exc:
        raise HTTPException(422, detail="Add valid resume content before rendering.") from exc
    tex = Path(directory) / "resume.tex"
    tex.write_text(latex, encoding="utf-8")
    result = compile_latex(tex)
    if result.pdf_path is None:
        raise HTTPException(503, detail=result.error_message or "PDF compilation unavailable.")
    return tex, result.pdf_path


@router.post("/preview")
def preview(draft: BuilderDraft, page: int = Query(default=1, ge=1, le=20)):
    with TemporaryDirectory(prefix="resume-builder-") as directory:
        _, path = _compile(draft, directory)
        try:
            import fitz
            with fitz.open(path) as pdf:
                if page > pdf.page_count:
                    raise HTTPException(404, detail="Page not found.")
                image = pdf[page - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                return Response(image.tobytes("png"), media_type="image/png", headers={
                    "Cache-Control": "no-store", "X-Page-Count": str(pdf.page_count)})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, detail="PDF preview could not be rendered.") from exc


@router.post("/source-pdf")
def source_pdf(draft: BuilderDraft):
    """Compile the current draft for immediate handoff to the review workflow."""
    with TemporaryDirectory(prefix="resume-builder-review-") as directory:
        _, path = _compile(draft, directory)
        return Response(
            path.read_bytes(),
            media_type="application/pdf",
            headers={"Cache-Control": "no-store",
                     "Content-Disposition": 'inline; filename="resume.pdf"'},
        )


@router.post("/export")
def export(draft: BuilderDraft):
    if not draft.full_name.strip():
        raise HTTPException(422, detail="Add your full name before exporting.")
    for entries in (draft.experiences, draft.projects):
        if any(not i.name.strip() or not any(p.strip() for p in i.points) for i in entries):
            raise HTTPException(422, detail="Each experience/project needs a name and at least one point.")
    for section in draft.custom_sections:
        if not section.entries or any(not i.name.strip() or not any(p.strip() for p in i.points) for i in section.entries):
            raise HTTPException(422, detail="Each custom section needs an entry with a name and at least one point.")
    if any(not i.name.strip() or not i.title.strip() for i in draft.education):
        raise HTTPException(422, detail="Each education entry needs a school and degree/diploma.")
    if any(not i.title.strip() for i in draft.experiences):
        raise HTTPException(422, detail="Each experience entry needs a job title.")
    if any(not i.name.strip() or not any(s.strip() for s in i.skills) for i in draft.skill_groups):
        raise HTTPException(422, detail="Each skill group needs a label and at least one skill.")
    with TemporaryDirectory(prefix="resume-builder-") as directory:
        tex, pdf = _compile(draft, directory)
        word = Path(directory) / "resume.docx"
        render_builder_word(draft, word)
        artifact_id = save_resume_artifacts(tex, pdf, word)
    return {"pdf_download_url": f"/api/artifacts/{artifact_id}/resume.pdf",
            "tex_download_url": f"/api/artifacts/{artifact_id}/resume.tex",
            "docx_download_url": f"/api/artifacts/{artifact_id}/resume.docx"}
