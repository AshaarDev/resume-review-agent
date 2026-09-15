"""Canonical resume policy loading, prompting, and evaluation tests."""

from core.policy_schemas import (
    BulletPolicyAnalysis,
    ContentPolicyAnalysis,
    MetricEmphasisAnalysis,
    PolicyFindingStatus,
)
from core.review_schemas import (
    ContentReviewResponse,
    LayoutAnalysisResponse,
    LayoutPageMetrics,
    ReviewStatus,
    VisualReviewResponse,
    VisualReviewResult,
)
from services.policy_evaluator import evaluate_resume_policy
from services.policy_prompt_builder import (
    build_content_policy_prompt,
    build_visual_policy_instructions,
)
from services.resume_policy import get_resume_quality_policy


def _content(years: float = 3, confidence: float = 0.9):
    return ContentReviewResponse(
        status=ReviewStatus.AVAILABLE,
        response="Reviewed.",
        analysis=ContentPolicyAnalysis(
            overall_feedback="Useful achievements, with room to improve.",
            estimated_relevant_experience_years=years,
            experience_estimate_confidence=confidence,
            bullets=[
                BulletPolicyAnalysis(
                    bullet_text="Reduced latency 40% by caching queries.",
                    has_accomplishment=True,
                    has_measurement=True,
                    has_method=True,
                    has_meaningful_metric=True,
                ),
                BulletPolicyAnalysis(
                    bullet_text="Helped maintain the application.",
                    has_accomplishment=False,
                    has_measurement=False,
                    has_method=True,
                    has_meaningful_metric=False,
                ),
            ],
        ),
    )


def _visual(coverage: float = 0.5, confidence: float = 0.9):
    return VisualReviewResponse(
        status=ReviewStatus.AVAILABLE,
        result=VisualReviewResult(
            visual_score=80,
            pass_status=True,
            strengths=[],
            issues=[],
            metric_emphasis=MetricEmphasisAnalysis(
                eligible_metric_count=2,
                emphasized_metric_count=1,
                coverage=coverage,
                confidence=confidence,
                unbolded_metrics=["40% latency reduction"],
            ),
        ),
    )


def _layout(densities: list[float]):
    return LayoutAnalysisResponse(
        status=ReviewStatus.AVAILABLE,
        page_count=len(densities),
        pages=[
            LayoutPageMetrics(
                page_number=index,
                width_points=612,
                height_points=792,
                text_density=density,
                font_sizes=[10] if density else [],
            )
            for index, density in enumerate(densities, start=1)
        ],
    )


def test_policy_loads_expected_version_and_rules():
    policy = get_resume_quality_policy()

    assert policy.policy_id == "resume-review"
    assert policy.version == "1.0"
    assert {rule.code for rule in policy.rules} == {
        "LOW_XYZ_BULLET_COVERAGE",
        "INSUFFICIENT_QUANTIFICATION",
        "EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE",
        "UNBOLDED_KEY_METRICS",
    }


def test_policy_prompts_are_model_specific_and_semantic():
    policy = get_resume_quality_policy()
    content_prompt = build_content_policy_prompt(policy)
    visual_prompt = build_visual_policy_instructions(policy)

    assert "LOW_XYZ_BULLET_COVERAGE" in content_prompt
    assert "literal wording or order" in content_prompt
    assert "UNBOLDED_KEY_METRICS" not in content_prompt
    assert "UNBOLDED_KEY_METRICS" in visual_prompt
    assert "meaningful achievement metric" in visual_prompt
    assert "LOW_XYZ_BULLET_COVERAGE" not in visual_prompt


def test_policy_evaluator_combines_content_visual_and_page_findings():
    findings = evaluate_resume_policy(
        get_resume_quality_policy(),
        _content(years=3),
        _visual(coverage=0.5),
        _layout([0.2, 0.15]),
        "pdf",
    )
    by_code = {finding.code: finding for finding in findings}

    assert by_code["LOW_XYZ_BULLET_COVERAGE"].status == (
        PolicyFindingStatus.MINOR_ISSUE
    )
    assert by_code["INSUFFICIENT_QUANTIFICATION"].status == (
        PolicyFindingStatus.MINOR_ISSUE
    )
    assert by_code["EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE"].status == (
        PolicyFindingStatus.MAJOR_ISSUE
    )
    assert by_code["UNBOLDED_KEY_METRICS"].status == (
        PolicyFindingStatus.MINOR_ISSUE
    )


def test_page_rule_allows_two_pages_at_five_years():
    findings = evaluate_resume_policy(
        get_resume_quality_policy(),
        _content(years=5),
        _visual(coverage=1),
        _layout([0.2, 0.15]),
        "pdf",
    )

    page_finding = next(
        finding
        for finding in findings
        if finding.code == "EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE"
    )
    assert page_finding.status == PolicyFindingStatus.PASSED
    assert page_finding.target_value == 2


def test_blank_document_page_is_not_counted_by_page_rule():
    findings = evaluate_resume_policy(
        get_resume_quality_policy(),
        _content(years=2),
        _visual(coverage=1),
        _layout([0.2, 0]),
        "pdf",
    )

    page_finding = next(
        finding
        for finding in findings
        if finding.code == "EXCESSIVE_PAGE_COUNT_FOR_EXPERIENCE"
    )
    assert page_finding.status == PolicyFindingStatus.PASSED
    assert page_finding.measured_value == 1


def test_low_confidence_metric_analysis_is_explicitly_unavailable():
    findings = evaluate_resume_policy(
        get_resume_quality_policy(),
        _content(),
        _visual(coverage=0.2, confidence=0.4),
        _layout([0.2]),
        "pdf",
    )

    metric_finding = next(
        finding
        for finding in findings
        if finding.code == "UNBOLDED_KEY_METRICS"
    )
    assert metric_finding.status == PolicyFindingStatus.UNAVAILABLE

