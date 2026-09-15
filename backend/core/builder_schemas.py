"""Bounded intake contracts for the non-AI resume editor."""
from typing import Annotated
from pydantic import BaseModel, Field

ShortPoint = Annotated[str, Field(max_length=700)]
Skill = Annotated[str, Field(max_length=100)]


class Entry(BaseModel):
    name: str = Field(default="", max_length=180)
    title: str = Field(default="", max_length=180)
    location: str = Field(default="", max_length=160)
    dates: str = Field(default="", max_length=100)
    stack: str = Field(default="", max_length=180)
    coursework: str = Field(default="", max_length=700)
    points: list[ShortPoint] = Field(default_factory=list, max_length=6)
    skills: list[Skill] = Field(default_factory=list, max_length=40)


class CustomSection(BaseModel):
    id: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    entries: list[Entry] = Field(default_factory=list, max_length=12)


class BuilderDraft(BaseModel):
    full_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=160)
    experiences: list[Entry] = Field(default_factory=list, max_length=12)
    education: list[Entry] = Field(default_factory=list, max_length=12)
    projects: list[Entry] = Field(default_factory=list, max_length=12)
    skill_groups: list[Entry] = Field(default_factory=list, max_length=12)
    custom_sections: list[CustomSection] = Field(default_factory=list, max_length=8)
    section_order: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list, max_length=12)
