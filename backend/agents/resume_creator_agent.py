"""Resume Creator Agent: assisted Luna drafting plus deterministic artifacts."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.config import settings
from core.creator_schemas import (
    ClaimLedgerEntry,
    CompilationStatus,
    CreatorAgentResult,
    CreatorMessage,
    GeneratedResumeDocument,
    ResumeArtifact,
    ResumeCreationBrief,
)
from core.policy_schemas import ResumeQualityPolicy
from services.artifact_store import save_resume_artifacts
from services.creator_service import (
    CreatorServiceError,
    generate_resume_document,
    refine_resume_document,
)
from services.creator_quality import CreatorQualityReport, assess_creator_output
from services.document_processor import PreparedDocument
from services.latex_compiler import LatexCompilationResult, compile_latex
from services.latex_renderer import (
    render_resume_latex,
    template_metadata,
)
from services.layout_analyzer import analyze_layout
from services.workflow_events import WorkflowEventSink, emit_workflow_event

logger = logging.getLogger(__name__)


@dataclass
class _DraftCandidate:
    document: GeneratedResumeDocument
    claims: list[ClaimLedgerEntry]
    tex_path: Path
    compilation: LatexCompilationResult
    quality: CreatorQualityReport
    review_feedback: list[str]


class ResumeCreatorAgent:
    """Create an editable assisted resume draft and compile it in one workspace."""

    def run(
        self,
        brief: ResumeCreationBrief,
        job_description: str,
        user_instructions: str,
        workspace_path: Path,
        policy: ResumeQualityPolicy,
        event_sink: Optional[WorkflowEventSink] = None,
    ) -> CreatorAgentResult:
        try:
            emit_workflow_event(
                event_sink,
                phase="draft_generation",
                status="started",
                message="Grounding the draft in the submitted source facts.",
                details={"source_fact_count": len(brief.source_facts)},
            )
            document = generate_resume_document(
                brief,
                policy,
                job_description,
                user_instructions,
            )
            emit_workflow_event(
                event_sink,
                phase="draft_generation",
                status="completed",
                message="The initial structured resume draft is ready.",
                details={
                    "experience_entries": len(document.experiences),
                    "project_entries": len(document.projects),
                    "education_entries": len(document.education),
                },
            )
            best = _compile_and_review_candidate(
                brief, document, policy, workspace_path, 0, event_sink
            )
            refinement_passes = 0
            quality_warnings: list[CreatorMessage] = []

            for pass_number in range(1, settings.CREATOR_MAX_REFINEMENT_PASSES + 1):
                if _is_release_ready(best):
                    break
                if best.compilation.status != CompilationStatus.COMPILED:
                    break
                try:
                    emit_workflow_event(
                        event_sink,
                        phase="refinement",
                        status="started",
                        message=f"Starting refinement pass {pass_number} from the best compiled draft.",
                        details={
                            "pass": pass_number,
                            "current_page_count": best.quality.page_count,
                            "current_issue_count": len(best.quality.issues),
                        },
                    )
                    revised_document = refine_resume_document(
                        brief,
                        policy,
                        best.document,
                        best.review_feedback,
                        job_description,
                        user_instructions,
                    )
                    refinement_passes += 1
                    candidate = _compile_and_review_candidate(
                        brief,
                        revised_document,
                        policy,
                        workspace_path,
                        pass_number,
                        event_sink,
                    )
                    if _candidate_score(candidate) < _candidate_score(best):
                        best = candidate
                        emit_workflow_event(
                            event_sink,
                            phase="refinement",
                            status="improved",
                            message=f"Refinement pass {pass_number} improved the compiled resume and was retained.",
                            details={
                                "pass": pass_number,
                                "page_count": candidate.quality.page_count,
                                "page_fill_ratio": candidate.quality.page_fill_ratio,
                                "remaining_issues": len(candidate.quality.issues),
                            },
                        )
                    else:
                        emit_workflow_event(
                            event_sink,
                            phase="refinement",
                            status="rejected",
                            message=f"Refinement pass {pass_number} did not improve the page and was discarded.",
                            details={
                                "pass": pass_number,
                                "page_count": candidate.quality.page_count,
                                "remaining_issues": len(candidate.quality.issues),
                            },
                        )
                except (CreatorServiceError, ValueError) as exc:
                    logger.warning("Creator quality refinement skipped: %s", exc)
                    quality_warnings.append(
                        CreatorMessage(
                            code="CREATOR_REFINEMENT_UNAVAILABLE",
                            message=(
                                "The best compiled draft was retained because a "
                                "quality refinement pass could not be completed."
                            ),
                        )
                    )
                    emit_workflow_event(
                        event_sink,
                        phase="refinement",
                        status="unavailable",
                        message="A refinement pass failed, so the best earlier draft was retained.",
                    )
                    break

            document = best.document
            claims = best.claims
            tex_path = best.tex_path
            compilation = best.compilation
            quality = best.quality
            release_ready = _is_release_ready(best)
            emit_workflow_event(
                event_sink,
                phase="quality_gate",
                status="passed" if release_ready else "needs_review",
                message=(
                    "The compiled resume passed the one-page quality gate."
                    if release_ready
                    else "The best compiled resume still needs user review."
                ),
                details={
                    "page_count": quality.page_count,
                    "page_fill_ratio": quality.page_fill_ratio,
                    "refinement_passes": refinement_passes,
                    "remaining_issues": len(quality.issues),
                },
            )

            artifact_id = save_resume_artifacts(
                tex_path, compilation.pdf_path
            )
            metadata = template_metadata()
            artifact = ResumeArtifact(
                artifact_id=artifact_id,
                template_id=metadata["template_id"],
                template_version=metadata["version"],
                compilation_status=compilation.status,
                tex_download_url=(
                    f"/api/artifacts/{artifact_id}/resume.tex"
                ),
                pdf_download_url=(
                    f"/api/artifacts/{artifact_id}/resume.pdf"
                    if compilation.pdf_path
                    else None
                ),
                error_code=compilation.error_code,
                error_message=compilation.error_message,
            )
            warnings = quality_warnings
            if compilation.status != CompilationStatus.COMPILED:
                warnings.append(
                    CreatorMessage(
                        code=compilation.error_code
                        or "LATEX_COMPILE_UNAVAILABLE",
                        message=compilation.error_message
                        or "Only the LaTeX source is available.",
                    )
                )
            if document.missing_information:
                warnings.append(
                    CreatorMessage(
                        code="CREATOR_MISSING_INFORMATION",
                        message=(
                            "The draft needs user confirmation for: "
                            + "; ".join(document.missing_information[:5])
                        ),
                    )
                )
            mock_count = sum(
                bullet.is_mock
                for entry in [*document.experiences, *document.projects]
                for bullet in entry.bullets
            )
            if mock_count:
                warnings.append(
                    CreatorMessage(
                        code="CREATOR_MOCK_CONTENT",
                        message=(
                            f"The draft contains {mock_count} AI-authored mock "
                            "bullet(s). Edit and verify them before submitting."
                        ),
                    )
                )
            if (
                compilation.status == CompilationStatus.COMPILED
                and quality.page_count != settings.CREATOR_TARGET_PAGE_COUNT
            ):
                warnings.append(
                    CreatorMessage(
                        code="CREATOR_PAGE_TARGET_UNMET",
                        message=(
                            "The refinement loop could not produce an exact "
                            f"{settings.CREATOR_TARGET_PAGE_COUNT}-page document "
                            f"after {refinement_passes} pass(es)."
                        ),
                    )
                )
            if quality.issues:
                warnings.append(
                    CreatorMessage(
                        code="CREATOR_QUALITY_NEEDS_REVIEW",
                        message=(
                            "The draft was optimized against the resume policy, "
                            "but some standards still need user-supplied evidence."
                        ),
                    )
                )
            return CreatorAgentResult(
                status=(
                    "completed"
                    if compilation.status == CompilationStatus.COMPILED
                    and release_ready
                    else "partial"
                ),
                model=settings.CREATOR_MODEL,
                policy_id=policy.policy_id,
                policy_version=policy.version,
                document=document,
                claims_ledger=claims,
                artifact=artifact,
                quality_status=(
                    "passed" if release_ready else "needs_review"
                ),
                quality_notes=quality.issues,
                refinement_passes=refinement_passes,
                final_page_count=quality.page_count,
                page_fill_ratio=quality.page_fill_ratio,
                warnings=warnings,
            )
        except CreatorServiceError as exc:
            return _failed_result(policy, exc.code, str(exc))
        except ValueError as exc:
            logger.warning("Creator output failed factual validation: %s", exc)
            return _failed_result(
                policy,
                "CREATOR_UNSUPPORTED_CLAIM",
                "The generated resume referenced unsupported source facts.",
            )
        except Exception:
            logger.exception("Resume Creator Agent failed")
            return _failed_result(
                policy,
                "CREATOR_AGENT_FAILED",
                "The Resume Creator Agent could not complete.",
            )


def _compile_and_review_candidate(
    brief: ResumeCreationBrief,
    document: GeneratedResumeDocument,
    policy: ResumeQualityPolicy,
    workspace_path: Path,
    pass_number: int,
    event_sink: Optional[WorkflowEventSink] = None,
) -> _DraftCandidate:
    """Compile one draft and review its real PDF using shared layout metrics."""

    claims = _build_and_validate_claims(brief, document)
    emit_workflow_event(
        event_sink,
        phase="pdf_compilation",
        status="started",
        message=(
            "Compiling the initial LaTeX draft into a PDF."
            if pass_number == 0
            else f"Compiling refinement pass {pass_number} into a new PDF."
        ),
        details={"pass": pass_number},
    )
    name = "resume.tex" if pass_number == 0 else f"resume-refined-{pass_number}.tex"
    tex_path = workspace_path / name
    tex_path.write_text(render_resume_latex(brief, document), encoding="utf-8")
    compilation = compile_latex(tex_path)
    emit_workflow_event(
        event_sink,
        phase="pdf_compilation",
        status=compilation.status.value,
        message=(
            "PDF compilation completed."
            if compilation.status == CompilationStatus.COMPILED
            else "PDF compilation was unavailable; preserving the LaTeX source."
        ),
        details={"pass": pass_number},
    )
    quality = assess_creator_output(
        brief, document, policy, compilation.pdf_path
    )
    feedback = list(quality.issues)
    emit_workflow_event(
        event_sink,
        phase="compiled_pdf_review",
        status="completed",
        message=(
            f"Measured {quality.page_count} page(s) with "
            f"{quality.page_fill_ratio:.0%} vertical fill."
            if quality.page_count is not None
            and quality.page_fill_ratio is not None
            else "Completed the deterministic quality review."
        ),
        details={
            "pass": pass_number,
            "page_count": quality.page_count,
            "page_fill_ratio": quality.page_fill_ratio,
            "issue_count": len(quality.issues),
        },
    )
    total_bullets = sum(
        len(entry.bullets)
        for entry in [*document.experiences, *document.projects]
    )
    feedback.append(
        "Current content inventory: "
        f"{len(document.experiences)} experience entries, "
        f"{len(document.projects)} project entries, and {total_bullets} bullets. "
        "Keep every user-supplied entry, but combine overlapping facts and trim "
        "lower-value mock bullets when space is tight."
    )

    if compilation.pdf_path and compilation.pdf_path.is_file():
        try:
            prepared = PreparedDocument(
                source_path=compilation.pdf_path,
                pdf_path=compilation.pdf_path,
                page_image_paths=[],
                page_count=quality.page_count or 0,
                file_type="pdf",
            )
            layout = analyze_layout(prepared)
            metrics = ", ".join(
                f"page {page.page_number}: density {page.text_density:.3f}, "
                f"minimum font {page.min_font_size or 0:.1f}pt"
                for page in layout.pages
            )
            if feedback and metrics:
                feedback.append(
                    "Compiled-PDF layout measurements from the review engine: "
                    + metrics
                    + "."
                )
            emit_workflow_event(
                event_sink,
                phase="layout_analysis",
                status="completed",
                message="Measured the compiled PDF layout and font geometry.",
                details={
                    "pass": pass_number,
                    "page_count": layout.page_count,
                    "minimum_font_pt": min(
                        (
                            page.min_font_size
                            for page in layout.pages
                            if page.min_font_size is not None
                        ),
                        default=None,
                    ),
                },
            )
        except Exception as exc:
            logger.warning("Creator layout review unavailable: %s", exc)
            emit_workflow_event(
                event_sink,
                phase="layout_analysis",
                status="unavailable",
                message="Detailed layout measurements were unavailable for this pass.",
                details={"pass": pass_number},
            )

    if quality.page_count != settings.CREATOR_TARGET_PAGE_COUNT:
        feedback.insert(
            0,
            "HARD PAGE CONSTRAINT: the compiled PDF is "
            f"{quality.page_count if quality.page_count is not None else 'an unknown number of'} "
            f"pages. It must compile to exactly {settings.CREATOR_TARGET_PAGE_COUNT} "
            "page. Preserve every user-supplied role, project, education item, "
            "skill, and meaningful metric. First remove or combine redundant mock "
            "content, then shorten wording and merge overlapping bullets. Return "
            "the entire revised document.",
        )
    elif (
        quality.page_fill_ratio is not None
        and quality.page_fill_ratio < settings.CREATOR_MIN_PAGE_FILL_RATIO
    ):
        feedback.insert(
            0,
            "HARD PAGE-FILL CONSTRAINT: the resume is one page but uses only "
            f"{quality.page_fill_ratio:.0%} of its height. Fill at least "
            f"{settings.CREATOR_MIN_PAGE_FILL_RATIO:.0%} with distinct, relevant "
            "XYZ bullets and useful sections.",
        )

    return _DraftCandidate(
        document=document,
        claims=claims,
        tex_path=tex_path,
        compilation=compilation,
        quality=quality,
        review_feedback=list(dict.fromkeys(feedback)),
    )


def _is_release_ready(candidate: _DraftCandidate) -> bool:
    return (
        candidate.compilation.status == CompilationStatus.COMPILED
        and candidate.quality.page_count == settings.CREATOR_TARGET_PAGE_COUNT
        and candidate.quality.page_fill_ratio is not None
        and candidate.quality.page_fill_ratio
        >= settings.CREATOR_MIN_PAGE_FILL_RATIO
        and not candidate.quality.issues
    )


def _candidate_score(candidate: _DraftCandidate) -> tuple[float, ...]:
    """Rank compiled candidates with exact page count as the first priority."""

    compiled_penalty = (
        0.0
        if candidate.compilation.status == CompilationStatus.COMPILED
        else 1.0
    )
    page_count = candidate.quality.page_count
    page_penalty = (
        abs(page_count - settings.CREATOR_TARGET_PAGE_COUNT)
        if page_count is not None
        else 99.0
    )
    fill_ratio = candidate.quality.page_fill_ratio or 0.0
    fill_penalty = max(0.0, settings.CREATOR_MIN_PAGE_FILL_RATIO - fill_ratio)
    return (
        compiled_penalty,
        float(page_penalty),
        fill_penalty,
        float(len(candidate.quality.issues)),
    )


def _build_and_validate_claims(
    brief: ResumeCreationBrief, document: GeneratedResumeDocument
) -> list[ClaimLedgerEntry]:
    allowed = {fact.fact_id for fact in brief.source_facts}
    claims: list[ClaimLedgerEntry] = []

    def add(
        section: str, text: str, source_ids: list[str], is_mock: bool = False
    ) -> None:
        if not source_ids or not set(source_ids).issubset(allowed):
            raise ValueError("Generated claim contains an unknown fact ID")
        claims.append(
            ClaimLedgerEntry(
                section=section,
                generated_text=text,
                source_fact_ids=source_ids,
                is_mock=is_mock,
            )
        )

    if document.professional_summary:
        add(
            "summary",
            document.professional_summary,
            document.professional_summary_source_fact_ids,
        )
    for entry in document.experiences:
        add(
            "experience",
            ", ".join(
                part
                for part in (
                    entry.role,
                    entry.organization,
                    entry.location,
                    entry.date_range,
                )
                if part
            ),
            entry.source_fact_ids,
        )
        for bullet in entry.bullets:
            add(
                "experience", bullet.text, bullet.source_fact_ids,
                bullet.is_mock,
            )
    for entry in document.projects:
        add(
            "project",
            ", ".join(
                part for part in (entry.name, entry.date_range) if part
            ),
            entry.source_fact_ids,
            entry.is_mock,
        )
        for bullet in entry.bullets:
            add("project", bullet.text, bullet.source_fact_ids, bullet.is_mock)
    for entry in document.education:
        add(
            "education",
            f"{entry.degree}, {entry.institution}",
            entry.source_fact_ids,
        )
    for group in document.skill_groups:
        add(
            "skills",
            f"{group.label}: {', '.join(group.skills)}",
            group.source_fact_ids,
        )
    return claims


def _failed_result(
    policy: ResumeQualityPolicy, code: str, message: str
) -> CreatorAgentResult:
    return CreatorAgentResult(
        status="failed",
        model=settings.CREATOR_MODEL,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        errors=[CreatorMessage(code=code, message=message)],
    )
