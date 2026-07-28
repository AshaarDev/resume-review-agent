"""Resume Review Agent: domain normalization over the existing review pipeline."""

import logging
import re
from pathlib import Path
from statistics import median

from core.policy_schemas import (
    PolicyFinding,
    PolicyFindingStatus,
    ResumeQualityPolicy,
)
from core.review_schemas import ReviewStatus, VisualIssueSeverity
from core.workflow_schemas import (
    AgentStatus,
    PriorityAction,
    ReviewAgentResult,
    WorkflowMessage,
)
from services.review_pipeline import run_review_pipeline
from services.policy_evaluator import evaluate_resume_policy
from services.resume_policy import get_resume_quality_policy

logger = logging.getLogger(__name__)

SMALL_BODY_FONT_PT = 9.5
VERY_SMALL_FONT_PT = 8.0
HIGH_TEXT_DENSITY = 0.60
LOW_TEXT_DENSITY = 0.10
PAGE_DIMENSION_VARIANCE = 0.03

MAX_CONTENT_ACTIONS = 5
MAX_LAYOUT_ACTIONS = 5
MAX_MINOR_VISUAL_ISSUES_FOR_SYNTHESIS = 5
MAX_SYNTHESIS_INPUT_CHARACTERS = 15_000
MAX_SUMMARY_PRIORITY_ACTIONS = 5


class ResumeReviewAgent:
    """Run the review capability and normalize its findings for orchestration."""

    def run(
        self,
        source_path: Path,
        file_type: str,
        job_description: str,
        user_instructions: str,
        workspace_path: Path,
        policy: ResumeQualityPolicy | None = None,
    ) -> ReviewAgentResult:
        del user_instructions  # Reserved for agent-specific behavior in a later phase.
        active_policy = policy or get_resume_quality_policy()
        try:
            review = run_review_pipeline(
                source_path,
                file_type,
                job_description,
                workspace_path,
                active_policy,
            )
        except Exception:
            logger.exception("Review pipeline failed completely")
            return ReviewAgentResult(
                status=AgentStatus.FAILED,
                content_review={
                    "status": "unavailable",
                    "error_code": "PIPELINE_FAILED",
                    "error_message": "The content review could not run.",
                },
                visual_review={
                    "status": "unavailable",
                    "error_code": "PIPELINE_FAILED",
                    "error_message": "The visual review could not run.",
                },
                layout_analysis={
                    "status": "unavailable",
                    "error_code": "PIPELINE_FAILED",
                    "error_message": "The layout analysis could not run.",
                },
                policy_id=active_policy.policy_id,
                policy_version=active_policy.version,
                errors=[
                    WorkflowMessage(
                        code="REVIEW_PIPELINE_FAILED",
                        message="The resume review pipeline could not run.",
                        source="resume_review_agent",
                    )
                ],
            )

        branches = (
            review.content_review,
            review.visual_review,
            review.layout_analysis,
        )
        available_count = sum(
            branch.status == ReviewStatus.AVAILABLE for branch in branches
        )
        status = (
            AgentStatus.COMPLETED
            if available_count == 3
            else AgentStatus.PARTIAL
            if available_count
            else AgentStatus.FAILED
        )

        indexed_actions: list[tuple[int, PriorityAction]] = []
        policy_findings = evaluate_resume_policy(
            active_policy,
            review.content_review,
            review.visual_review,
            review.layout_analysis,
            file_type,
        )
        for action in self._policy_actions(policy_findings):
            indexed_actions.append((len(indexed_actions), action))
        for action in self._visual_actions(review.visual_review):
            indexed_actions.append((len(indexed_actions), action))
        for action in self._layout_actions(review.layout_analysis, file_type):
            indexed_actions.append((len(indexed_actions), action))
        for action in self._content_actions(review.content_review):
            indexed_actions.append((len(indexed_actions), action))
        indexed_actions.sort(
            key=lambda item: (
                item[1].priority,
                item[1].source,
                item[0],
            )
        )

        warnings: list[WorkflowMessage] = []
        for source, branch in (
            ("content_review", review.content_review),
            ("visual_review", review.visual_review),
            ("layout_analysis", review.layout_analysis),
        ):
            if branch.status == ReviewStatus.UNAVAILABLE:
                warnings.append(
                    WorkflowMessage(
                        code=branch.error_code or "REVIEW_BRANCH_UNAVAILABLE",
                        message=branch.error_message
                        or f"The {source.replace('_', ' ')} is unavailable.",
                        source=source,
                    )
                )
        for finding in policy_findings:
            if finding.status == PolicyFindingStatus.UNAVAILABLE:
                warnings.append(
                    WorkflowMessage(
                        code=f"{finding.code}_UNAVAILABLE",
                        message=finding.recommendation,
                        source=finding.source,
                    )
                )

        return ReviewAgentResult(
            status=status,
            content_review=review.content_review,
            visual_review=review.visual_review,
            layout_analysis=review.layout_analysis,
            policy_id=active_policy.policy_id,
            policy_version=active_policy.version,
            policy_findings=policy_findings,
            proposed_actions=[item[1] for item in indexed_actions],
            warnings=warnings,
        )

    @staticmethod
    def _policy_actions(
        findings: list[PolicyFinding],
    ) -> list[PriorityAction]:
        actions = []
        for finding in findings:
            if finding.status not in {
                PolicyFindingStatus.MAJOR_ISSUE,
                PolicyFindingStatus.MINOR_ISSUE,
            }:
                continue
            actions.append(
                PriorityAction(
                    priority=(
                        1
                        if finding.status == PolicyFindingStatus.MAJOR_ISSUE
                        else 2
                    ),
                    source="policy",
                    issue_code=finding.code,
                    title=finding.description,
                    recommendation=finding.recommendation,
                )
            )
        return actions

    @staticmethod
    def _visual_actions(visual_review) -> list[PriorityAction]:
        if (
            visual_review.status != ReviewStatus.AVAILABLE
            or visual_review.result is None
        ):
            return []
        priority_by_severity = {
            VisualIssueSeverity.CRITICAL: 1,
            VisualIssueSeverity.MAJOR: 2,
            VisualIssueSeverity.MINOR: 3,
        }
        major_actions: list[PriorityAction] = []
        minor_actions: list[PriorityAction] = []
        for issue in visual_review.result.issues:
            action = PriorityAction(
                priority=priority_by_severity[issue.severity],
                source="visual",
                issue_code=issue.code.value,
                title=issue.description,
                recommendation=issue.recommendation,
            )
            (
                minor_actions
                if issue.severity == VisualIssueSeverity.MINOR
                else major_actions
            ).append(action)
        return major_actions + minor_actions[:MAX_MINOR_VISUAL_ISSUES_FOR_SYNTHESIS]

    @staticmethod
    def _content_actions(content_review) -> list[PriorityAction]:
        if (
            content_review.status != ReviewStatus.AVAILABLE
            or not content_review.response
        ):
            return []
        candidates: list[str] = []
        for raw_line in content_review.response.splitlines():
            line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
            lowered = line.lower()
            if len(line) >= 12 and (
                raw_line.lstrip().startswith(("-", "*", "•"))
                or re.match(r"^\s*\d+[.)]", raw_line)
                or any(
                    marker in lowered
                    for marker in ("recommend", "should", "improve", "consider")
                )
            ):
                candidates.append(line)
            if len(candidates) == MAX_CONTENT_ACTIONS:
                break
        return [
            PriorityAction(
                priority=2,
                source="content",
                issue_code="CONTENT_RECOMMENDATION",
                title=line[:120],
                recommendation=line,
            )
            for line in candidates
        ]

    @staticmethod
    def _layout_actions(layout, file_type: str) -> list[PriorityAction]:
        if layout.status != ReviewStatus.AVAILABLE or not layout.pages:
            return []
        actions: list[PriorityAction] = []
        is_image = file_type.lower().lstrip(".") in {"jpg", "jpeg", "png"}
        reviewable_pages = (
            layout.pages
            if is_image
            else [
                page
                for page in layout.pages
                if page.font_sizes or page.text_density > 0.001
            ]
        )
        if not reviewable_pages:
            return []
        if not is_image:
            small_pages = sorted(
                {
                    page.page_number
                    for page in reviewable_pages
                    if (
                        page.median_font_size is not None
                        and page.median_font_size < SMALL_BODY_FONT_PT
                    )
                    or (
                        page.dominant_font_size is not None
                        and page.dominant_font_size < SMALL_BODY_FONT_PT
                    )
                }
            )
            very_small_pages = sorted(
                page.page_number
                for page in reviewable_pages
                if page.min_font_size is not None
                and page.min_font_size < VERY_SMALL_FONT_PT
            )
            high_density_pages = sorted(
                page.page_number
                for page in reviewable_pages
                if page.text_density > HIGH_TEXT_DENSITY
            )
            low_density_pages = sorted(
                page.page_number
                for page in reviewable_pages
                if page.font_sizes and page.text_density < LOW_TEXT_DENSITY
            )
            page_sets = (
                (
                    small_pages,
                    "SMALL_BODY_FONT",
                    "Body text may be too small",
                    "Increase the dominant body font to at least 9.5 pt.",
                ),
                (
                    very_small_pages,
                    "VERY_SMALL_TEXT",
                    "Some text is extremely small",
                    "Increase text below 8 pt or remove nonessential fine print.",
                ),
                (
                    high_density_pages,
                    "HIGH_TEXT_DENSITY",
                    "Page content is visually dense",
                    "Reduce or redistribute content and add breathing room.",
                ),
                (
                    low_density_pages,
                    "LOW_TEXT_DENSITY",
                    "Page has unusually low text density",
                    "Rebalance content and whitespace across the page.",
                ),
            )
            for pages, code, title, recommendation in page_sets:
                if pages:
                    actions.append(
                        PriorityAction(
                            priority=2,
                            source="layout",
                            issue_code=code,
                            title=title,
                            recommendation=(
                                f"{recommendation} Affected pages: "
                                + ", ".join(map(str, pages))
                                + "."
                            ),
                        )
                    )

        if len(reviewable_pages) > 1:
            median_width = median(
                page.width_points for page in reviewable_pages
            )
            median_height = median(
                page.height_points for page in reviewable_pages
            )
            inconsistent = [
                page.page_number
                for page in reviewable_pages
                if abs(page.width_points - median_width) / median_width
                > PAGE_DIMENSION_VARIANCE
                or abs(page.height_points - median_height) / median_height
                > PAGE_DIMENSION_VARIANCE
            ]
            if inconsistent:
                actions.append(
                    PriorityAction(
                        priority=2,
                        source="layout",
                        issue_code="INCONSISTENT_PAGE_DIMENSIONS",
                        title="Page dimensions are inconsistent",
                        recommendation=(
                            "Use one page size and orientation throughout. "
                            "Affected pages: "
                            + ", ".join(map(str, inconsistent))
                            + "."
                        ),
                    )
                )
        return actions[:MAX_LAYOUT_ACTIONS]
