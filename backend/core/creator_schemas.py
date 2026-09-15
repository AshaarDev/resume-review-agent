"""Contracts for factual resume creation, artifacts, and Creator Agent output."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ResumeSourceFact(BaseModel):
    """One user-supplied fact that generated claims can cite."""

    fact_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=2, max_length=1000)


class ResumeCreationBrief(BaseModel):
    """Structured factual intake for a new resume."""

    full_name: str = Field(min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=80)
    location: Optional[str] = Field(default=None, max_length=160)
    links: list[str] = Field(default_factory=list, max_length=6)
    target_role: Optional[str] = Field(default=None, max_length=160)
    source_facts: list[ResumeSourceFact] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def unique_fact_ids(self) -> "ResumeCreationBrief":
        ids = [fact.fact_id for fact in self.source_facts]
        if len(ids) != len(set(ids)):
            raise ValueError("Resume source fact IDs must be unique")
        return self


class GeneratedResumeBullet(BaseModel):
    text: str = Field(min_length=1, max_length=700)
    bold_phrases: list[str] = Field(default_factory=list, max_length=4)
    source_fact_ids: list[str] = Field(min_length=1, max_length=8)


class GeneratedResumeEntry(BaseModel):
    organization: str = Field(min_length=1, max_length=180)
    role: str = Field(min_length=1, max_length=180)
    location: str = Field(default="", max_length=160)
    date_range: str = Field(default="", max_length=100)
    source_fact_ids: list[str] = Field(min_length=1, max_length=8)
    bullets: list[GeneratedResumeBullet] = Field(min_length=1, max_length=8)


class GeneratedProjectEntry(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    stack: str = Field(default="", max_length=180)
    date_range: str = Field(default="", max_length=100)
    url: Optional[str] = Field(default=None, max_length=500)
    source_fact_ids: list[str] = Field(min_length=1, max_length=8)
    bullets: list[GeneratedResumeBullet] = Field(min_length=1, max_length=6)


class GeneratedEducationEntry(BaseModel):
    institution: str = Field(min_length=1, max_length=180)
    degree: str = Field(min_length=1, max_length=220)
    location: str = Field(default="", max_length=160)
    date_range: str = Field(default="", max_length=100)
    details: list[str] = Field(default_factory=list, max_length=4)
    source_fact_ids: list[str] = Field(min_length=1, max_length=8)


class GeneratedSkillGroup(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    skills: list[str] = Field(min_length=1, max_length=40)
    source_fact_ids: list[str] = Field(min_length=1, max_length=12)


class GeneratedResumeDocument(BaseModel):
    """Structured Luna output rendered deterministically into LaTeX."""

    professional_summary: Optional[str] = Field(default=None, max_length=800)
    professional_summary_source_fact_ids: list[str] = Field(
        default_factory=list, max_length=12
    )
    experiences: list[GeneratedResumeEntry] = Field(default_factory=list)
    projects: list[GeneratedProjectEntry] = Field(default_factory=list)
    education: list[GeneratedEducationEntry] = Field(default_factory=list)
    skill_groups: list[GeneratedSkillGroup] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    estimated_relevant_experience_years: Optional[float] = Field(
        default=None, ge=0, le=60
    )
    experience_estimate_confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def has_resume_content(self) -> "GeneratedResumeDocument":
        if self.professional_summary and not self.professional_summary_source_fact_ids:
            raise ValueError("Professional summary must cite source facts")
        if (
            not self.professional_summary
            and self.professional_summary_source_fact_ids
        ):
            raise ValueError(
                "Summary source facts require a professional summary"
            )
        if not any(
            (self.experiences, self.projects, self.education, self.skill_groups)
        ):
            raise ValueError("Generated resume must contain at least one section")
        return self


class ClaimLedgerEntry(BaseModel):
    section: str
    generated_text: str
    source_fact_ids: list[str]


class CompilationStatus(str, Enum):
    COMPILED = "compiled"
    SOURCE_ONLY = "source_only"
    FAILED = "failed"


class ResumeArtifact(BaseModel):
    artifact_id: str
    template_id: str
    template_version: str
    compilation_status: CompilationStatus
    tex_download_url: str
    pdf_download_url: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class CreatorMessage(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    source: str = "resume_creator_agent"


class CreatorAgentResult(BaseModel):
    status: Literal["completed", "partial", "failed"]
    model: str
    policy_id: str
    policy_version: str
    document: Optional[GeneratedResumeDocument] = None
    claims_ledger: list[ClaimLedgerEntry] = Field(default_factory=list)
    artifact: Optional[ResumeArtifact] = None
    requires_user_review: bool = True
    quality_status: Literal["passed", "needs_review", "unavailable"] = (
        "unavailable"
    )
    quality_notes: list[str] = Field(default_factory=list)
    warnings: list[CreatorMessage] = Field(default_factory=list)
    errors: list[CreatorMessage] = Field(default_factory=list)
