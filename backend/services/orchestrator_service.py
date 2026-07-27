"""GPT-5.6 Luna orchestrator for final review synthesis with deterministic fallback."""

import json
import logging
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from core.config import settings
from core.workflow_schemas import (
    AgentStatus,
    OrchestratorSummary,
    PriorityAction,
    ReviewAgentResult,
)

logger = logging.getLogger(__name__)

# Action caps for synthesis input
MAX_MINOR_VISUAL_ISSUES_FOR_SYNTHESIS = 5


def synthesize_review_response(
    review_result: ReviewAgentResult,
    job_description: str,
    user_instructions: str,
) -> OrchestratorSummary:
    """Generate final synthesis using GPT-5.6 Luna or deterministic fallback.
    
    Args:
        review_result: Structured result from Resume Review Agent
        job_description: Optional job description context
        user_instructions: Optional user instructions
        
    Returns:
        OrchestratorSummary with overall assessment and priority actions
    """
    # Early exit: skip Luna if all branches failed
    if review_result.status == AgentStatus.FAILED:
        return _deterministic_failed_summary()

    # Try Luna synthesis
    try:
        return _synthesize_with_luna(review_result, job_description, user_instructions)
    except Exception as exc:
        logger.warning("Luna synthesis unavailable, using deterministic fallback: %s", exc)
        return _deterministic_fallback_summary(review_result)


def _synthesize_with_luna(
    review_result: ReviewAgentResult,
    job_description: str,
    user_instructions: str,
) -> OrchestratorSummary:
    """Use GPT-5.6 Luna Responses API for synthesis."""
    
    # Prepare synthesis input with action caps
    synthesis_input = _prepare_synthesis_input(review_result)
    
    # Build prompt
    prompt = _build_synthesis_prompt(
        synthesis_input, job_description, user_instructions
    )
    
    # Check input size
    if len(prompt) > 15_000:
        logger.info("Synthesis input exceeds 15k chars, compacting")
        prompt = _compact_synthesis_input(prompt)
    
    # Initialize OpenAI client
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        # Use Responses API with Pydantic schema
        response = client.beta.chat.completions.parse(
            model=settings.ORCHESTRATOR_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume reviewer synthesizing structured review findings.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=OrchestratorSummary,
            timeout=settings.ORCHESTRATOR_TIMEOUT_SECONDS,
        )
        
        if response.choices[0].message.parsed:
            return response.choices[0].message.parsed
        
        # Fallback if parsed is None
        raise ValueError("Luna returned empty parsed response")
        
    except Exception as exc:
        logger.warning("Luna synthesis failed: %s", exc)
        raise


def _prepare_synthesis_input(review_result: ReviewAgentResult) -> dict:
    """Prepare review data for synthesis with action caps applied."""
    
    # Separate actions by priority
    critical_major_actions = [
        a for a in review_result.proposed_actions if a.priority <= 2
    ]
    minor_actions = [
        a for a in review_result.proposed_actions if a.priority > 2
    ]
    
    # Cap minor actions
    capped_minor = minor_actions[:MAX_MINOR_VISUAL_ISSUES_FOR_SYNTHESIS]
    
    # Combine (all critical/major + capped minor)
    synthesis_actions = critical_major_actions + capped_minor
    
    return {
        "content_review": review_result.content_review.model_dump(mode="json"),
        "visual_review": review_result.visual_review.model_dump(mode="json"),
        "layout_analysis": review_result.layout_analysis.model_dump(mode="json"),
        "proposed_actions": [a.model_dump(mode="json") for a in synthesis_actions],
        "agent_status": review_result.status.value,
    }


def _build_synthesis_prompt(
    synthesis_input: dict,
    job_description: str,
    user_instructions: str,
) -> str:
    """Build the synthesis prompt for Luna."""
    
    prompt_parts = [
        "Synthesize the following resume review findings into a concise summary.",
        "",
        "Review Data:",
        json.dumps(synthesis_input, separators=(",", ":")),
    ]
    
    if job_description:
        prompt_parts.extend([
            "",
            f"Job Description: {job_description}",
        ])
    
    if user_instructions:
        prompt_parts.extend([
            "",
            f"User Instructions: {user_instructions}",
        ])
    
    prompt_parts.extend([
        "",
        "Requirements:",
        "- Provide an overall assessment of the resume",
        "- List top 3 strengths (if any)",
        "- Prioritize the top 5 most important actions",
        "- Never invent findings not in the review data",
        "- Never alter scores or severity levels",
        "- Never omit critical or major issues",
        "- Distinguish unavailable branches from successful ones",
        "- Recommend a clear next step",
    ])
    
    return "\n".join(prompt_parts)


def _compact_synthesis_input(prompt: str) -> str:
    """Compact the synthesis input to stay under character limit."""
    # Simple compaction: remove extra whitespace
    # More sophisticated compaction could truncate individual fields
    return " ".join(prompt.split())


def _deterministic_failed_summary() -> OrchestratorSummary:
    """Return a deterministic summary when all review branches failed."""
    return OrchestratorSummary(
        overall_assessment="The resume review could not be completed due to processing errors.",
        top_strengths=[],
        priority_actions=[],
        next_step="Please try uploading your resume again. If the issue persists, verify the file is a valid PDF or DOCX.",
    )


def _deterministic_fallback_summary(
    review_result: ReviewAgentResult,
) -> OrchestratorSummary:
    """Generate deterministic summary when Luna is unavailable."""
    
    # Extract top actions by priority
    top_actions = sorted(
        review_result.proposed_actions,
        key=lambda a: (a.priority, a.source)
    )[:5]
    
    # Build assessment based on available branches
    available_branches = []
    if review_result.content_review.status.value == "available":
        available_branches.append("content")
    if review_result.visual_review.status.value == "available":
        available_branches.append("visual")
    if review_result.layout_analysis.status.value == "available":
        available_branches.append("layout")
    
    if not available_branches:
        return _deterministic_failed_summary()
    
    assessment = f"Resume review completed ({', '.join(available_branches)} analysis available)."
    
    # Extract strengths from visual review if available
    strengths = []
    if (review_result.visual_review.status.value == "available" and
        review_result.visual_review.result):
        strengths = review_result.visual_review.result.strengths[:3]
    
    # Determine next step
    if review_result.status == AgentStatus.COMPLETED:
        next_step = "Address the priority actions to improve your resume."
    elif review_result.status == AgentStatus.PARTIAL:
        next_step = "Address the available findings. Some review branches were unavailable."
    else:
        next_step = "Review the available findings and retry for complete analysis."
    
    return OrchestratorSummary(
        overall_assessment=assessment,
        top_strengths=strengths,
        priority_actions=top_actions,
        next_step=next_step,
    )
