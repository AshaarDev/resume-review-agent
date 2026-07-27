"""Resume Review Agent with deterministic layout analysis and action prioritization."""

import logging
from pathlib import Path
from statistics import median
from typing import Optional

from core.review_schemas import (
    ReviewStatus,
    UnifiedResumeReviewResponse,
    VisualIssueSeverity,
)
from core.workflow_schemas import AgentStatus, PriorityAction, ReviewAgentResult
from services.review_pipeline import analyze_resume_bytes

logger = logging.getLogger(__name__)

# Layout thresholds - tested heuristics, not environment variables
SMALL_BODY_FONT_PT = 9.5
VERY_SMALL_FONT_PT = 8.0
HIGH_TEXT_DENSITY = 0.60
LOW_TEXT_DENSITY = 0.10
PAGE_DIMENSION_VARIANCE = 0.03

# Action caps to control latency and cost
MAX_CONTENT_ACTIONS = 5
MAX_LAYOUT_ACTIONS = 5
MAX_MINOR_VISUAL_ISSUES_FOR_SYNTHESIS = 5
MAX_SYNTHESIS_INPUT_CHARACTERS = 15_000
MAX_SUMMARY_PRIORITY_ACTIONS = 5


class ResumeReviewAgent:
    """Agent that wraps the existing review pipeline and generates prioritized actions."""

    def run(
        self,
        source_path: Path,
        file_type: str,
        job_description: str,
        user_instructions: str,
        workspace_path: Path,
    ) -> ReviewAgentResult:
        """Execute the review pipeline and generate prioritized actions.
        
        Args:
            source_path: Path to the uploaded resume file
            file_type: Normalized file extension
            job_description: Optional job description for tailored review
            user_instructions: Optional user-specific instructions
            workspace_path: Temporary workspace for this request
            
        Returns:
            ReviewAgentResult with structured findings and prioritized actions
        """
        # Read the file and call the existing review pipeline
        file_bytes = source_path.read_bytes()
        
        try:
            unified_review = analyze_resume_bytes(
                file_bytes, file_type, job_description
            )
        except Exception as exc:
            logger.exception("Review pipeline failed completely")
            return ReviewAgentResult(
                status=AgentStatus.FAILED,
                content_review={"status": "unavailable", "error_code": "PIPELINE_FAILED"},
                visual_review={"status": "unavailable", "error_code": "PIPELINE_FAILED"},
                layout_analysis={"status": "unavailable", "error_code": "PIPELINE_FAILED"},
                proposed_actions=[],
                warnings=[],
                errors=[f"Review pipeline failed: {str(exc)}"],
            )

        # Determine agent status based on available branches
        content_available = unified_review.content_review.status == ReviewStatus.AVAILABLE
        visual_available = unified_review.visual_review.status == ReviewStatus.AVAILABLE
        layout_available = unified_review.layout_analysis.status == ReviewStatus.AVAILABLE

        if content_available and visual_available and layout_available:
            agent_status = AgentStatus.COMPLETED
        elif content_available or visual_available or layout_available:
            agent_status = AgentStatus.PARTIAL
        else:
            agent_status = AgentStatus.FAILED

        # Generate deterministic layout actions
        layout_actions = self._generate_layout_actions(unified_review)

        # Extract visual issues as priority actions
        visual_actions = self._extract_visual_actions(unified_review)

        # Extract content actions (best effort parsing)
        content_actions = self._extract_content_actions(unified_review)

        # Combine and sort all actions
        all_actions = layout_actions + visual_actions + content_actions
        all_actions.sort(key=lambda a: (a.priority, a.source))

        # Collect warnings
        warnings = []
        if unified_review.content_review.status == ReviewStatus.UNAVAILABLE:
            warnings.append(
                f"Content review unavailable: {unified_review.content_review.error_message}"
            )
        if unified_review.visual_review.status == ReviewStatus.UNAVAILABLE:
            warnings.append(
                f"Visual review unavailable: {unified_review.visual_review.error_message}"
            )
        if unified_review.layout_analysis.status == ReviewStatus.UNAVAILABLE:
            warnings.append(
                f"Layout analysis unavailable: {unified_review.layout_analysis.error_message}"
            )

        return ReviewAgentResult(
            status=agent_status,
            content_review=unified_review.content_review,
            visual_review=unified_review.visual_review,
            layout_analysis=unified_review.layout_analysis,
            proposed_actions=all_actions,
            warnings=warnings,
            errors=[],
        )

    def _generate_layout_actions(
        self, review: UnifiedResumeReviewResponse
    ) -> list[PriorityAction]:
        """Generate deterministic layout actions from metrics."""
        if review.layout_analysis.status != ReviewStatus.AVAILABLE:
            return []

        layout = review.layout_analysis
        actions = []

        # Skip font/density checks for image-only resumes
        is_image_only = all(
            page.text_density == 0.0 for page in layout.pages
        )

        if not is_image_only and layout.pages:
            # Check for small fonts
            small_font_pages = []
            very_small_pages = []

            for page in layout.pages:
                if page.median_font_size and page.median_font_size < SMALL_BODY_FONT_PT:
                    small_font_pages.append(page.page_number)
                if page.dominant_font_size and page.dominant_font_size < SMALL_BODY_FONT_PT:
                    if page.page_number not in small_font_pages:
                        small_font_pages.append(page.page_number)
                if page.min_font_size and page.min_font_size < VERY_SMALL_FONT_PT:
                    very_small_pages.append(page.page_number)

            # Deduplicate small font findings into one action
            if small_font_pages:
                pages_str = ", ".join(f"page {p}" for p in sorted(small_font_pages))
                actions.append(
                    PriorityAction(
                        priority=2,
                        source="layout",
                        issue_code="SMALL_FONT",
                        title="Small body text detected",
                        recommendation=f"Increase font size to at least {SMALL_BODY_FONT_PT}pt on {pages_str}",
                    )
                )

            if very_small_pages:
                pages_str = ", ".join(f"page {p}" for p in sorted(very_small_pages))
                actions.append(
                    PriorityAction(
                        priority=1,
                        source="layout",
                        issue_code="VERY_SMALL_FONT",
                        title="Very small text detected",
                        recommendation=f"Text below {VERY_SMALL_FONT_PT}pt is difficult to read on {pages_str}",
                    )
                )

            # Check text density
            for page in layout.pages:
                if page.text_density > HIGH_TEXT_DENSITY:
                    actions.append(
                        PriorityAction(
                            priority=2,
                            source="layout",
                            issue_code="HIGH_DENSITY",
                            title=f"Page {page.page_number} is crowded",
                            recommendation=f"Reduce text density from {page.text_density:.1%} to improve readability",
                        )
                    )
                elif page.text_density < LOW_TEXT_DENSITY:
                    actions.append(
                        PriorityAction(
                            priority=3,
                            source="layout",
                            issue_code="LOW_DENSITY",
                            title=f"Page {page.page_number} has sparse content",
                            recommendation="Consider consolidating content or using space more effectively",
                        )
                    )

        # Check for inconsistent page dimensions
        if len(layout.pages) > 1:
            widths = [p.width_points for p in layout.pages]
            heights = [p.height_points for p in layout.pages]
            median_width = median(widths)
            median_height = median(heights)

            inconsistent_pages = []
            for page in layout.pages:
                width_variance = abs(page.width_points - median_width) / median_width
                height_variance = abs(page.height_points - median_height) / median_height
                if width_variance > PAGE_DIMENSION_VARIANCE or height_variance > PAGE_DIMENSION_VARIANCE:
                    inconsistent_pages.append(page.page_number)

            if inconsistent_pages:
                pages_str = ", ".join(f"page {p}" for p in inconsistent_pages)
                actions.append(
                    PriorityAction(
                        priority=2,
                        source="layout",
                        issue_code="INCONSISTENT_DIMENSIONS",
                        title="Inconsistent page dimensions",
                        recommendation=f"Standardize page size across {pages_str}",
                    )
                )

        # Cap layout actions
        return actions[:MAX_LAYOUT_ACTIONS]

    def _extract_visual_actions(
        self, review: UnifiedResumeReviewResponse
    ) -> list[PriorityAction]:
        """Convert visual issues to priority actions."""
        if review.visual_review.status != ReviewStatus.AVAILABLE:
            return []
        if not review.visual_review.result:
            return []

        actions = []
        for issue in review.visual_review.result.issues:
            # Map severity to priority
            if issue.severity == VisualIssueSeverity.CRITICAL:
                priority = 1
            elif issue.severity == VisualIssueSeverity.MAJOR:
                priority = 2
            else:  # MINOR
                priority = 3

            actions.append(
                PriorityAction(
                    priority=priority,
                    source="visual",
                    issue_code=issue.code.value,
                    title=issue.description,
                    recommendation=issue.recommendation,
                )
            )

        return actions

    def _extract_content_actions(
        self, review: UnifiedResumeReviewResponse
    ) -> list[PriorityAction]:
        """Extract actionable items from content review (best effort)."""
        if review.content_review.status != ReviewStatus.AVAILABLE:
            return []
        if not review.content_review.response:
            return []

        # Best-effort parsing of GPT content review
        # This is a simple heuristic - could be improved with structured output
        actions = []
        response_text = review.content_review.response

        # Look for common action indicators
        lines = response_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Simple heuristic: lines starting with bullet points or numbers
            # that contain action words
            action_indicators = ["consider", "add", "remove", "improve", "update", "revise", "include"]
            if any(indicator in line.lower() for indicator in action_indicators):
                # Extract a reasonable title (first 80 chars)
                title = line[:80] + "..." if len(line) > 80 else line
                actions.append(
                    PriorityAction(
                        priority=2,  # Content actions are medium priority
                        source="content",
                        issue_code=None,
                        title=title,
                        recommendation=line,
                    )
                )

            if len(actions) >= MAX_CONTENT_ACTIONS:
                break

        return actions[:MAX_CONTENT_ACTIONS]
