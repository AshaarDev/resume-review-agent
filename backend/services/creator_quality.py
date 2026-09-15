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

    cited_fact_ids = set(document.professional_summary_source_fact_ids)
    for entry in document.experiences:
        cited_fact_ids.update(entry.source_fact_ids)
        for bullet in entry.bullets:
            cited_fact_ids.update(bullet.source_fact_ids)
    for entry in document.projects:
        cited_fact_ids.update(entry.source_fact_ids)
        for bullet in entry.bullets:
            cited_fact_ids.update(bullet.source_fact_ids)
    for entry in document.education:
        cited_fact_ids.update(entry.source_fact_ids)
    for group in document.skill_groups:
        cited_fact_ids.update(group.source_fact_ids)
    uncited_fact_ids = [
        fact.fact_id
        for fact in brief.source_facts
        if fact.fact_id not in cited_fact_ids
    ]
    if uncited_fact_ids:
        issues.append(
            "Preserve every user-supplied source fact in the resume. Incorporate "
            "or merge the content associated with these uncited fact IDs: "
            + ", ".join(uncited_fact_ids)
            + "."
        )

    if not document.professional_summary:
        issues.append(
            "Add a concise role-targeted professional summary grounded in the supplied facts."
        )

    # Required depth adapts to the number of entries that must share one page.
    # A fixed four-bullets-per-role rule fights the page-fit constraint for
    # candidates with several roles and causes the refinement loop to oscillate.
    entry_count = len(document.experiences) + len(document.projects)
    experience_minimum = 4 if entry_count <= 2 else 3 if entry_count <= 4 else 2
    project_minimum = 3 if entry_count <= 2 else 2
    shallow_entries = [
        f"{entry.role} at {entry.organization}"
        for entry in document.experiences
        if len(entry.bullets) < experience_minimum
    ] + [
        f"project {entry.name}"
        for entry in document.projects
        if len(entry.bullets) < project_minimum
    ]
    if shallow_entries:
        issues.append(
            "Develop additional distinct XYZ-style bullets, using clearly marked "
            "mock suggestions when the intake is sparse, for: "
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
    # Creation has a stricter product contract than review: the generated
    # artifact must target exactly one page, even when the review policy would
    # permit an experienced candidate to use two.
    allowed_pages = settings.CREATOR_TARGET_PAGE_COUNT
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
