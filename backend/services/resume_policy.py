"""Load and expose the canonical versioned Resume Quality Policy."""

import json
from functools import lru_cache
from pathlib import Path

from core.policy_schemas import ResumeQualityPolicy

POLICY_PATH = (
    Path(__file__).resolve().parent.parent
    / "policies"
    / "resume-review-policy-v1.json"
)


@lru_cache(maxsize=1)
def get_resume_quality_policy() -> ResumeQualityPolicy:
    """Load once and fail fast if the required policy is invalid."""

    return ResumeQualityPolicy.model_validate_json(
        POLICY_PATH.read_text(encoding="utf-8")
    )


def serialize_resume_quality_policy() -> str:
    return json.dumps(
        get_resume_quality_policy().model_dump(mode="json"),
        separators=(",", ":"),
    )
