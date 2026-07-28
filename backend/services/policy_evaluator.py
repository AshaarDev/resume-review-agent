"""Deterministically evaluate structured model outputs against policy rules."""

from core.policy_schemas import (
    PolicyFinding,
    PolicyFindingStatus,
    ResumeQualityPolicy,
)
from core.review_schemas import (
    ContentReviewResponse,
    LayoutAnalysisResponse,
    ReviewStatus,
    VisualReviewResponse,
)


def evaluate_resume_policy(
    policy: ResumeQualityPolicy,
    content: ContentReviewResponse,
    visual: VisualReviewResponse,
    layout: LayoutAnalysisResponse,
    file_type: str,
) -> list[PolicyFinding]:
    return [
        _evaluate_xyz(policy, content),
        _evaluate_quantification(policy, content),
        _evaluate_page_count(policy, content, layout, file_type),
        _evaluate_metric_emphasis(policy, visual),
    ]


def _coverage_status(value: float, target: float, major_below: float):
    if value < major_below:
        return PolicyFindingStatus.MAJOR_ISSUE
    if value < target:
        return PolicyFindingStatus.MINOR_ISSUE
    return PolicyFindingStatus.PASSED


def _evaluate_xyz(
    policy: ResumeQualityPolicy, content: ContentReviewResponse
) -> PolicyFinding:
    rule = policy.rule("LOW_XYZ_BULLET_COVERAGE")
    analysis = content.analysis
    if content.status != ReviewStatus.AVAILABLE or not analysis or not analysis.bullets:
        return _unavailable(rule, "gpt_content", "XYZ bullet analysis was unavailable.")
    compliant = [
        bullet
        for bullet in analysis.bullets
        if bullet.has_accomplishment
        and bullet.has_measurement
        and bullet.has_method
    ]
    coverage = len(compliant) / len(analysis.bullets)
    target = rule.target or 0
    status = _coverage_status(coverage, target, rule.major_below or 0)
    evidence = [
        bullet.bullet_text
        for bullet in analysis.bullets
        if bullet not in compliant
    ][:3]
    return PolicyFinding(
        code=rule.code,
        status=status,
        source="content_review",
        description=rule.description,
        measured_value=coverage,
        target_value=target,
        evidence=evidence,
        recommendation=(
            "Rewrite weak achievement bullets to state the result, meaningful "
            "measurement, and method used."
        ),
    )


def _evaluate_quantification(
    policy: ResumeQualityPolicy, content: ContentReviewResponse
) -> PolicyFinding:
    rule = policy.rule("INSUFFICIENT_QUANTIFICATION")
    analysis = content.analysis
    if content.status != ReviewStatus.AVAILABLE or not analysis or not analysis.bullets:
        return _unavailable(
            rule, "gpt_content", "Quantification analysis was unavailable."
        )
    quantified = [
        bullet for bullet in analysis.bullets if bullet.has_meaningful_metric
    ]
    coverage = len(quantified) / len(analysis.bullets)
    target = rule.target or 0
    return PolicyFinding(
        code=rule.code,
        status=_coverage_status(coverage, target, rule.major_below or 0),
        source="content_review",
        description=rule.description,
        measured_value=coverage,
        target_value=target,
        evidence=[
            bullet.bullet_text
            for bullet in analysis.bullets
            if not bullet.has_meaningful_metric
        ][:3],
        recommendation=(
            "Add credible measures such as time saved, percentage improvement, "
            "team size, money, users, reliability, or scale."
        ),
    )


def _evaluate_page_count(
    policy: ResumeQualityPolicy,
    content: ContentReviewResponse,
    layout: LayoutAnalysisResponse,
    file_type: str,
) -> PolicyFinding:
    rule = policy.rule("EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE")
    analysis = content.analysis
    if (
        not analysis
        or analysis.estimated_relevant_experience_years is None
        or analysis.experience_estimate_confidence
        < (rule.minimum_experience_confidence or 0)
        or layout.status != ReviewStatus.AVAILABLE
    ):
        return _unavailable(
            rule,
            "review_agent",
            "Page-length compliance could not be determined confidently.",
        )
    is_image = file_type.lower().lstrip(".") in {"jpg", "jpeg", "png"}
    pages = (
        layout.pages
        if is_image
        else [
            page
            for page in layout.pages
            if page.font_sizes or page.text_density > 0.001
        ]
    )
    page_count = len(pages)
    years = analysis.estimated_relevant_experience_years
    threshold = rule.experience_threshold_years or 5
    allowed = (
        rule.max_pages_below_threshold
        if years < threshold
        else rule.max_pages_at_or_above_threshold
    ) or 1
    return PolicyFinding(
        code=rule.code,
        status=(
            PolicyFindingStatus.MAJOR_ISSUE
            if page_count > allowed
            else PolicyFindingStatus.PASSED
        ),
        source="review_agent",
        description=rule.description,
        measured_value=float(page_count),
        target_value=float(allowed),
        evidence=[
            f"{years:.1f} estimated years of relevant experience",
            f"{page_count} nonblank content page(s)",
        ],
        recommendation=(
            f"Keep the resume to no more than {allowed} nonblank content "
            f"page{'s' if allowed != 1 else ''} for this experience level."
        ),
    )


def _evaluate_metric_emphasis(
    policy: ResumeQualityPolicy, visual: VisualReviewResponse
) -> PolicyFinding:
    rule = policy.rule("UNBOLDED_KEY_METRICS")
    emphasis = visual.result.metric_emphasis if visual.result else None
    if (
        visual.status != ReviewStatus.AVAILABLE
        or emphasis is None
        or emphasis.coverage is None
        or emphasis.confidence < (rule.minimum_analysis_confidence or 0)
    ):
        return _unavailable(
            rule,
            "gemini_visual",
            "Metric-emphasis analysis was unavailable or low confidence.",
        )
    target = rule.target or 0
    return PolicyFinding(
        code=rule.code,
        status=_coverage_status(
            emphasis.coverage, target, rule.major_below or 0
        ),
        source="visual_review",
        description=rule.description,
        measured_value=emphasis.coverage,
        target_value=target,
        evidence=emphasis.unbolded_metrics[:3],
        recommendation=(
            "Bold the most important achievement metrics selectively; do not "
            "bold dates, versions, or every number."
        ),
    )


def _unavailable(rule, source: str, message: str) -> PolicyFinding:
    return PolicyFinding(
        code=rule.code,
        status=PolicyFindingStatus.UNAVAILABLE,
        source=source,
        description=rule.description,
        recommendation=message,
    )
