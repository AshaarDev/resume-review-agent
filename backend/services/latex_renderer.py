"""Safely render structured resume data into the approved Harshibar template."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from core.creator_schemas import (
    GeneratedResumeBullet,
    GeneratedResumeDocument,
    ResumeCreationBrief,
)

TEMPLATE_DIR = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "resumes"
    / "harshibar"
)
TEMPLATE_PATH = TEMPLATE_DIR / "template.tex"
METADATA_PATH = TEMPLATE_DIR / "metadata.json"

_LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: str) -> str:
    return "".join(_LATEX_REPLACEMENTS.get(char, char) for char in value)


def template_metadata() -> dict:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def render_resume_latex(
    brief: ResumeCreationBrief, document: GeneratedResumeDocument
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "%%__HEADER__%%": _render_header(brief),
        "%%__SUMMARY__%%": _render_summary(document),
        "%%__EXPERIENCE__%%": _render_experience(document),
        "%%__PROJECTS__%%": _render_projects(document),
        "%%__EDUCATION__%%": _render_education(document),
        "%%__SKILLS__%%": _render_skills(document),
    }
    for marker, rendered in replacements.items():
        template = template.replace(marker, rendered)
    return template


def _render_header(brief: ResumeCreationBrief) -> str:
    contact_parts = []
    if brief.phone:
        contact_parts.append(r"\faPhone* \texttt{" + latex_escape(brief.phone) + "}")
    if brief.email:
        contact_parts.append(
            r"\faEnvelope \hspace{2pt} \texttt{"
            + latex_escape(brief.email)
            + "}"
        )
    if brief.location:
        contact_parts.append(
            r"\faMapMarker* \hspace{2pt}\texttt{"
            + latex_escape(brief.location)
            + "}"
        )
    for link in brief.links:
        if _safe_url(link):
            contact_parts.append(
                r"\faGlobe \hspace{2pt}\href{"
                + link
                + r"}{\myuline{"
                + latex_escape(_link_label(link))
                + "}}"
            )
    joined = r" \hspace{1pt} $|$ \hspace{1pt} ".join(contact_parts)
    contact_line = rf"    \small {joined} \\ \vspace{{-3pt}}" if joined else ""
    return "\n".join(
        [
            r"\begin{center}",
            rf"    \textbf{{\Huge {latex_escape(brief.full_name)}}} \\ \vspace{{5pt}}",
            contact_line,
            r"\end{center}",
        ]
    )


def _render_summary(document: GeneratedResumeDocument) -> str:
    if not document.professional_summary:
        return ""
    return "\n".join(
        [
            r"\section{SUMMARY}",
            r"\small{" + latex_escape(document.professional_summary) + "}",
        ]
    )


def _render_experience(document: GeneratedResumeDocument) -> str:
    if not document.experiences:
        return ""
    lines = [r"\section{EXPERIENCE}", r"\resumeSubHeadingListStart"]
    for entry in document.experiences:
        lines.extend(
            [
                r"\resumeSubheading",
                f"  {{{latex_escape(entry.organization)}}}"
                f"{{{latex_escape(entry.date_range)}}}",
                f"  {{{latex_escape(entry.role)}}}"
                f"{{{latex_escape(entry.location)}}}",
                r"\resumeItemListStart",
            ]
        )
        lines.extend(_render_bullet(bullet) for bullet in entry.bullets)
        lines.append(r"\resumeItemListEnd")
    lines.append(r"\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _render_projects(document: GeneratedResumeDocument) -> str:
    if not document.projects:
        return ""
    lines = [r"\section{PROJECTS}", r"\resumeSubHeadingListStart"]
    for entry in document.projects:
        name = latex_escape(entry.name)
        if entry.url and _safe_url(entry.url):
            name = rf"\href{{{entry.url}}}{{\myuline{{{name}}}}}"
        lines.extend(
            [
                r"\resumeProjectHeading",
                rf"  {{\textbf{{{name}}}}}{{{latex_escape(entry.date_range)}}}",
                r"\resumeItemListStart",
            ]
        )
        lines.extend(_render_bullet(bullet) for bullet in entry.bullets)
        lines.append(r"\resumeItemListEnd")
    lines.append(r"\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _render_education(document: GeneratedResumeDocument) -> str:
    if not document.education:
        return ""
    lines = [r"\section{EDUCATION}", r"\resumeSubHeadingListStart"]
    for entry in document.education:
        lines.extend(
            [
                r"\resumeSubheading",
                f"  {{{latex_escape(entry.institution)}}}"
                f"{{{latex_escape(entry.date_range)}}}",
                f"  {{{latex_escape(entry.degree)}}}"
                f"{{{latex_escape(entry.location)}}}",
            ]
        )
        if entry.details:
            lines.append(r"\resumeItemListStart")
            lines.extend(
                rf"\resumeItem{{{latex_escape(detail)}}}"
                for detail in entry.details
            )
            lines.append(r"\resumeItemListEnd")
    lines.append(r"\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _render_skills(document: GeneratedResumeDocument) -> str:
    if not document.skill_groups:
        return ""
    groups = []
    for group in document.skill_groups:
        skills = ", ".join(latex_escape(skill) for skill in group.skills)
        groups.append(
            rf"\textbf{{{latex_escape(group.label)}}} {{: {skills}}}"
            r"\vspace{2pt} \\"
        )
    return "\n".join(
        [
            r"\section{SKILLS}",
            r"\begin{itemize}[leftmargin=0in, label={}]",
            r"\small{\item{",
            *groups,
            r"}}",
            r"\end{itemize}",
        ]
    )


def _render_bullet(bullet: GeneratedResumeBullet) -> str:
    rendered = _render_emphasis(bullet.text, bullet.bold_phrases)
    return rf"\resumeItem{{{rendered}}}"


def _render_emphasis(text: str, phrases: list[str]) -> str:
    usable = sorted(
        {phrase for phrase in phrases if phrase and phrase in text},
        key=len,
        reverse=True,
    )
    if not usable:
        return latex_escape(text)
    pattern = re.compile("|".join(re.escape(phrase) for phrase in usable))
    rendered = []
    cursor = 0
    for match in pattern.finditer(text):
        rendered.append(latex_escape(text[cursor : match.start()]))
        rendered.append(r"\textbf{" + latex_escape(match.group(0)) + "}")
        cursor = match.end()
    rendered.append(latex_escape(text[cursor:]))
    return "".join(rendered)


def _safe_url(value: str) -> bool:
    if any(
        char in value
        for char in ("{", "}", "\\", "\n", "\r", "%", "#", "&")
    ):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _link_label(value: str) -> str:
    parsed = urlparse(value)
    return (parsed.netloc + parsed.path).rstrip("/")[:60]
