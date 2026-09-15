"""Adapt manual entries to the shared template without any AI calls."""
from core.builder_schemas import BuilderDraft
from core.creator_schemas import GeneratedResumeDocument, ResumeCreationBrief
from services.latex_renderer import (
    latex_escape,
    render_inline_latex,
    render_resume_latex,
)


def render_builder_latex(draft: BuilderDraft) -> str:
    def bullets(item):
        return [{"text": text.strip(), "source_fact_ids": ["manual"]}
                for text in item.points if text.strip()]
    experiences = [{"organization": i.name.strip() or "Company", "role": i.title.strip() or "Role",
                    "location": i.location, "date_range": i.dates, "source_fact_ids": ["manual"],
                    "bullets": bullets(i)} for i in draft.experiences if bullets(i)]
    projects = [{"name": i.name.strip() or "Project", "stack": i.stack.strip(),
                 "date_range": i.dates, "source_fact_ids": ["manual"], "bullets": bullets(i)}
                for i in draft.projects if bullets(i)]
    education = [{"institution": i.name.strip() or "School", "degree": i.title.strip() or "Degree / diploma",
                  "location": i.location, "date_range": i.dates, "source_fact_ids": ["manual"],
                  "details": ([f"Relevant coursework: {i.coursework}"] if i.coursework.strip() else [])}
                 for i in draft.education if i.name.strip() or i.title.strip()]
    skills = [{"label": i.name.strip() or "Skills", "skills": [s.strip() for s in i.skills if s.strip()],
               "source_fact_ids": ["manual"]} for i in draft.skill_groups if any(s.strip() for s in i.skills)]
    custom_blocks = {}
    for index, section in enumerate(draft.custom_sections):
        custom_lines = []
        populated = [i for i in section.entries if any(p.strip() for p in i.points)]
        if not populated:
            continue
        custom_lines.extend([rf"\section{{{latex_escape(section.name.strip().upper())}}}", r"\resumeSubHeadingListStart"])
        for item in populated:
            name = item.name.strip() or "Entry"
            if item.location.strip():
                name += f", {item.location.strip()}"
            custom_lines.append(
                rf"\resumeSubheading{{{latex_escape(name)}}}{{{latex_escape(item.dates)}}}"
                rf"{{{latex_escape(item.title)}}}{{}}"
            )
            custom_lines.append(r"\resumeItemListStart")
            custom_lines.extend(
                rf"\resumeItem{{{render_inline_latex(p.strip())}}}"
                for p in item.points if p.strip()
            )
            custom_lines.append(r"\resumeItemListEnd")
        custom_lines.append(r"\resumeSubHeadingListEnd")
        custom_blocks[f"custom:{section.id or index}"] = "\n".join(custom_lines)
    if not any((experiences, projects, education, skills, custom_blocks)):
        raise ValueError("Add a point, education entry, or skill to render your resume.")
    document = (GeneratedResumeDocument(experiences=experiences, projects=projects, education=education, skill_groups=skills)
                if any((experiences, projects, education, skills)) else None)
    brief = ResumeCreationBrief(full_name=draft.full_name.strip() or "Your name", email=draft.email or None,
                                phone=draft.phone or None, location=draft.location or None,
                                source_facts=[{"fact_id": "manual", "text": "User-authored resume content"}])
    return render_resume_latex(brief, document, ordered_blocks=custom_blocks, section_order=draft.section_order)
