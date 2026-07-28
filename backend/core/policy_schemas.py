"""Validated schemas for versioned resume-quality policies and findings."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class PolicyRuleCategory(str, Enum):
    CONTENT = "content"
    VISUAL = "visual"
    CROSS_BRANCH = "cross_branch"


class PolicyEvaluator(str, Enum):
    GPT_CONTENT = "gpt_content"
    GEMINI_VISUAL = "gemini_visual"
    REVIEW_AGENT = "review_agent"


class PolicyRule(BaseModel):
    code: str = Field(min_length=1)
    category: PolicyRuleCategory
    description: str = Field(min_length=1)
    evaluator: PolicyEvaluator
    guidance: str = Field(min_length=1)
    target: Optional[float] = Field(default=None, ge=0, le=1)
    major_below: Optional[float] = Field(default=None, ge=0, le=1)
    experience_threshold_years: Optional[float] = Field(default=None, ge=0)
    max_pages_below_threshold: Optional[int] = Field(default=None, ge=1)
    max_pages_at_or_above_threshold: Optional[int] = Field(default=None, ge=1)
    minimum_experience_confidence: Optional[float] = Field(
        default=None, ge=0, le=1
    )
    minimum_analysis_confidence: Optional[float] = Field(
        default=None, ge=0, le=1
    )


class ResumeQualityPolicy(BaseModel):
    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    rules: list[PolicyRule] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_rule_codes(self) -> "ResumeQualityPolicy":
        codes = [rule.code for rule in self.rules]
        if len(codes) != len(set(codes)):
            raise ValueError("Policy rule codes must be unique")
        return self

    def rule(self, code: str) -> PolicyRule:
        for rule in self.rules:
            if rule.code == code:
                return rule
        raise KeyError(f"Policy rule is not configured: {code}")

    def rules_for(self, evaluator: PolicyEvaluator) -> list[PolicyRule]:
        return [rule for rule in self.rules if rule.evaluator == evaluator]


class PolicyFindingStatus(str, Enum):
    PASSED = "passed"
    MINOR_ISSUE = "minor_issue"
    MAJOR_ISSUE = "major_issue"
    UNAVAILABLE = "unavailable"


class PolicyFinding(BaseModel):
    code: str
    status: PolicyFindingStatus
    source: str
    description: str
    measured_value: Optional[float] = None
    target_value: Optional[float] = None
    evidence: list[str] = Field(default_factory=list)
    recommendation: str


class BulletPolicyAnalysis(BaseModel):
    bullet_text: str
    has_accomplishment: bool
    has_measurement: bool
    has_method: bool
    has_meaningful_metric: bool
    suggested_rewrite: Optional[str] = None


class ContentPolicyAnalysis(BaseModel):
    overall_feedback: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    estimated_relevant_experience_years: Optional[float] = Field(
        default=None, ge=0
    )
    experience_estimate_confidence: float = Field(ge=0, le=1)
    bullets: list[BulletPolicyAnalysis] = Field(default_factory=list)


class MetricEmphasisAnalysis(BaseModel):
    eligible_metric_count: int = Field(ge=0)
    emphasized_metric_count: int = Field(ge=0)
    coverage: Optional[float] = Field(default=None, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    unbolded_metrics: list[str] = Field(default_factory=list)
