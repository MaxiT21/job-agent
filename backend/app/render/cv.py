"""Render a TailoredCV to .docx."""

from __future__ import annotations

from pathlib import Path

from docx.shared import Pt

from app.render.common import contact_header, heading, new_document, save
from app.schemas import JobPosting, Profile, TailoredCV

SECTION_TITLES = {
    "en": {"summary": "Summary", "experience": "Experience", "project": "Projects",
           "education": "Education", "certificate": "Certificates", "skills": "Skills"},
    "es": {"summary": "Perfil", "experience": "Experiencia", "project": "Proyectos",
           "education": "Formación", "certificate": "Certificados", "skills": "Habilidades"},
    "ca": {"summary": "Perfil", "experience": "Experiència", "project": "Projectes",
           "education": "Formació", "certificate": "Certificats", "skills": "Habilitats"},
}  # fmt: skip


def render_cv(profile: Profile, cv: TailoredCV, posting: JobPosting, out_dir: Path) -> Path:
    titles = SECTION_TITLES.get(posting.language.value, SECTION_TITLES["en"])
    doc = new_document()
    contact_header(doc, profile)

    heading(doc, titles["summary"])
    doc.add_paragraph(cv.summary.text)

    # Entries grouped by kind, keeping the relevance order chosen by the agent.
    for kind in ("experience", "project", "education", "certificate"):
        entries = [(e, profile.item(e.item_id)) for e in cv.entries]
        entries = [(e, it) for e, it in entries if it and it.kind == kind]
        if not entries:
            continue
        heading(doc, titles[kind])
        for entry, item in entries:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.add_run(item.title).bold = True
            if item.org:
                p.add_run(f" — {item.org}")
            if item.period:
                p.add_run(f"  ({item.period})").italic = True
            for line in entry.bullets:
                b = doc.add_paragraph(line.text, style="List Bullet")
                b.paragraph_format.space_after = Pt(0)

    if cv.skills:
        heading(doc, titles["skills"])
        doc.add_paragraph(", ".join(cv.skills))

    return save(doc, out_dir, "cv.docx")
