"""Deterministic quality gate for generated resume drafts and compiled PDFs."""

from dataclasses import dataclass
from pathlib import Path
import re

from core.config import settings
from core.creator_schemas import GeneratedResumeDocument, ResumeCreationBrief
from core.policy_schemas import ResumeQualityPolicy

_ACTION_VERBS = {
    "accelerated", "achieved", "automated", "built", "created", "cut",
    "delivered", "designed", "developed", "drove", "enabled", "engineered",
    "generated", "grew", "implemented", "improved", "increased", "launched",
    "led", "managed", "optimized", "reduced", "saved", "scaled",
    "spearheaded", "streamlined", "strengthened", "supported",
}
_METHOD_MARKERS = (
    " by ", " through ", " using ", " via ", " with ", " leveraging ",
    " implementing ", " developing ", " building ", " automating ",
)
_METRIC_PATTERN = re.compile(
    r"(?:\$\s?\d[\d,.]*|\b\d+(?:\.\d+)?\s?(?:%|x|k|m|million|billion|"
    r"users?|customers?|clients?|files?|requests?|hours?|minutes?|days?|weeks?|"
    r"months?|members?|engineers?|developers?|stakeholders?|people|records?))(?!\w)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CreatorQualityReport:
    issues: list[str]
    page_count: int | None = None
    page_fill_ratio: float | None = None

    @property
    def passed(self) -> bool:
        return not self.issues


def assess_creator_output(
    brief: ResumeCreationBrief,
    document: GeneratedResumeDocument,
    policy: ResumeQualityPolicy,
    pdf_path: Path | None = None,
) -> CreatorQualityReport:
    """Check creator policy coverage and page use without another model call."""

    issues: list[str] = []
    bullets = [
        bullet
        for entry in document.experiences
        for bullet in entry.bullets
    ] + [bullet for entry in document.projects for bullet in entry.bullets]

    if not document.professional_summary:
        issues.append(
            "Add a concise role-targeted professional summary grounded in the supplied facts."
        )

    shallow_entries = [
        f"{entry.role} at {entry.organization}"
        for entry in document.experiences
        if len(entry.bullets) < 2
    ] + [
        f"project {entry.name}"
        for entry in document.projects
        if len(entry.bullets) < 2
    ]
    if shallow_entries:
        issues.append(
            "Develop additional distinct, supported XYZ-style bullets for: "
            + "; ".join(shallow_entries[:4])
            + "."
        )

    weak_bullets = [
        bullet.text
        for bullet in bullets
        if not _has_action_and_method(bullet.text)
    ]
    if bullets and len(weak_bullets) / len(bullets) > 0.3:
        issues.append(
            "Rewrite weak bullets to state the accomplishment and method clearly; "
            "use the full XYZ pattern whenever a supported measurement exists."
        )

    source_facts = {fact.fact_id: fact.text for fact in brief.source_facts}
    lost_metrics: list[str] = []
    unbolded_metrics: list[str] = []
    quantified = 0
    for bullet in bullets:
        bullet_metrics = _meaningful_metrics(bullet.text)
        if bullet_metrics:
            quantified += 1
        supported_metrics = {
            metric
            for source_id in bullet.source_fact_ids
            for metric in _meaningful_metrics(source_facts.get(source_id, ""))
        }
        if supported_metrics and not bullet_metrics:
            lost_metrics.append(bullet.text)
        for metric in bullet_metrics:
            if not any(metric in phrase for phrase in bullet.bold_phrases):
                unbolded_metrics.append(metric)

    if lost_metrics:
        issues.append(
            "Preserve the meaningful measurements supplied by the user in the bullets that cite them."
        )
    if unbolded_metrics:
        issues.append(
            "Add every supported achievement metric to bold_phrases, including: "
            + ", ".join(list(dict.fromkeys(unbolded_metrics))[:6])
            + "."
        )

    quantification_rule = policy.rule("INSUFFICIENT_QUANTIFICATION")
    target = quantification_rule.target or 0.6
    source_has_metrics = any(
        _meaningful_metrics(fact.text) for fact in brief.source_facts
    )
    if bullets and source_has_metrics and quantified / len(bullets) < target:
        issues.append(
            "Increase meaningful quantification toward the policy target using only measurements present in the source facts."
        )

    page_count, fill_ratio = _inspect_pdf(pdf_path)
    allowed_pages = _allowed_pages(document, policy)
    if page_count is not None and page_count > allowed_pages:
        issues.append(
            f"Condense the resume to {allowed_pages} page{'s' if allowed_pages > 1 else ''} "
            "while preserving the strongest role-relevant evidence."
        )
    if (
        page_count == 1
        and fill_ratio is not None
        and fill_ratio < settings.CREATOR_MIN_PAGE_FILL_RATIO
    ):
        issues.append(
            "The compiled page has excessive unused space. Strengthen supported bullets, "
            "include omitted applicable sections, and use the available page more completely."
        )

    return CreatorQualityReport(
        issues=list(dict.fromkeys(issues)),
        page_count=page_count,
        page_fill_ratio=fill_ratio,
    )


def _has_action_and_method(text: str) -> bool:
    words = re.findall(r"[A-Za-z]+", text.lower())
    has_action = bool(words and (words[0] in _ACTION_VERBS or words[0].endswith("ed")))
    lowered = f" {text.lower()} "
    return has_action and any(marker in lowered for marker in _METHOD_MARKERS)


def _meaningful_metrics(text: str) -> list[str]:
    return [match.group(0).strip() for match in _METRIC_PATTERN.finditer(text)]


def _allowed_pages(
    document: GeneratedResumeDocument, policy: ResumeQualityPolicy
) -> int:
    rule = policy.rule("EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE")
    experienced = (
        document.estimated_relevant_experience_years is not None
        and document.experience_estimate_confidence
        >= (rule.minimum_experience_confidence or 0.6)
        and document.estimated_relevant_experience_years
        >= (rule.experience_threshold_years or 5)
    )
    return (
        rule.max_pages_at_or_above_threshold or 2
        if experienced
        else rule.max_pages_below_threshold or 1
    )


def _inspect_pdf(pdf_path: Path | None) -> tuple[int | None, float | None]:
    if pdf_path is None or not pdf_path.is_file():
        return None, None
    try:
        import fitz

        with fitz.open(pdf_path) as pdf:
            if pdf.page_count == 0:
                return 0, 0.0
            page = pdf[-1]
            blocks = [
                block
                for block in page.get_text("blocks")
                if len(block) >= 5 and str(block[4]).strip()
            ]
            if not blocks:
                return pdf.page_count, 0.0
            bottom = max(float(block[3]) for block in blocks)
            return pdf.page_count, min(bottom / max(page.rect.height, 1), 1.0)
    except Exception:
        return None, None
