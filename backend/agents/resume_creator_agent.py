"""Resume Creator Agent: factual Luna generation plus deterministic artifacts."""

import logging
from pathlib import Path

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
from services.creator_quality import assess_creator_output
from services.latex_compiler import compile_latex
from services.latex_renderer import (
    render_resume_latex,
    template_metadata,
)

logger = logging.getLogger(__name__)


class ResumeCreatorAgent:
    """Create a source-grounded resume and compile it in one workspace."""

    def run(
        self,
        brief: ResumeCreationBrief,
        job_description: str,
        user_instructions: str,
        workspace_path: Path,
        policy: ResumeQualityPolicy,
    ) -> CreatorAgentResult:
        try:
            document = generate_resume_document(
                brief,
                policy,
                job_description,
                user_instructions,
            )
            claims = _build_and_validate_claims(brief, document)
            latex = render_resume_latex(brief, document)
            tex_path = workspace_path / "resume.tex"
            tex_path.write_text(latex, encoding="utf-8")
            compilation = compile_latex(tex_path)
            quality = assess_creator_output(
                brief, document, policy, compilation.pdf_path
            )
            quality_warnings: list[CreatorMessage] = []

            if (
                compilation.status == CompilationStatus.COMPILED
                and quality.issues
                and settings.CREATOR_MAX_REFINEMENT_PASSES > 0
            ):
                try:
                    candidate = refine_resume_document(
                        brief,
                        policy,
                        document,
                        quality.issues,
                        job_description,
                        user_instructions,
                    )
                    candidate_claims = _build_and_validate_claims(
                        brief, candidate
                    )
                    candidate_tex_path = workspace_path / "resume-refined.tex"
                    candidate_tex_path.write_text(
                        render_resume_latex(brief, candidate),
                        encoding="utf-8",
                    )
                    candidate_compilation = compile_latex(candidate_tex_path)
                    candidate_quality = assess_creator_output(
                        brief,
                        candidate,
                        policy,
                        candidate_compilation.pdf_path,
                    )
                    if (
                        candidate_compilation.status
                        == CompilationStatus.COMPILED
                        and len(candidate_quality.issues)
                        <= len(quality.issues)
                    ):
                        document = candidate
                        claims = candidate_claims
                        tex_path = candidate_tex_path
                        compilation = candidate_compilation
                        quality = candidate_quality
                except (CreatorServiceError, ValueError) as exc:
                    logger.warning("Creator quality refinement skipped: %s", exc)
                    quality_warnings.append(
                        CreatorMessage(
                            code="CREATOR_REFINEMENT_UNAVAILABLE",
                            message=(
                                "The initial grounded draft was retained because "
                                "the quality refinement could not be completed."
                            ),
                        )
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
                    else "partial"
                ),
                model=settings.CREATOR_MODEL,
                policy_id=policy.policy_id,
                policy_version=policy.version,
                document=document,
                claims_ledger=claims,
                artifact=artifact,
                quality_status=(
                    "passed" if quality.passed else "needs_review"
                ),
                quality_notes=quality.issues,
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


def _build_and_validate_claims(
    brief: ResumeCreationBrief, document: GeneratedResumeDocument
) -> list[ClaimLedgerEntry]:
    allowed = {fact.fact_id for fact in brief.source_facts}
    claims: list[ClaimLedgerEntry] = []

    def add(section: str, text: str, source_ids: list[str]) -> None:
        if not source_ids or not set(source_ids).issubset(allowed):
            raise ValueError("Generated claim contains an unknown fact ID")
        claims.append(
            ClaimLedgerEntry(
                section=section,
                generated_text=text,
                source_fact_ids=source_ids,
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
            add("experience", bullet.text, bullet.source_fact_ids)
    for entry in document.projects:
        add(
            "project",
            ", ".join(
                part for part in (entry.name, entry.date_range) if part
            ),
            entry.source_fact_ids,
        )
        for bullet in entry.bullets:
            add("project", bullet.text, bullet.source_fact_ids)
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
