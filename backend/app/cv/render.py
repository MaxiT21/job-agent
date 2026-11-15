"""Render a TailoredCV to .docx with python-docx.

Single-column, no tables/graphics: ATS parsers read it reliably.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.config import settings
from app.schemas import JobPosting, Profile, TailoredCV

SECTION_TITLES = {
    "en": {
        "summary": "Summary",
        "experience": "Experience",
        "project": "Projects",
        "education": "Education",
        "certificate": "Certificates",
        "skills": "Skills",
    },
    "es": {
        "summary": "Perfil",
        "experience": "Experiencia",
        "project": "Proyectos",
        "education": "Formación",
        "certificate": "Certificados",
        "skills": "Habilidades",
    },
    "ca": {
        "summary": "Perfil",
        "experience": "Experiència",
        "project": "Projectes",
        "education": "Formació",
        "certificate": "Certificats",
        "skills": "Habilitats",
    },
}
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)


def _heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = ACCENT


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def render_cv(profile: Profile, cv: TailoredCV, posting: JobPosting) -> Path:
    titles = SECTION_TITLES.get(posting.language.value, SECTION_TITLES["en"])
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for section in doc.sections:
        section.left_margin = section.right_margin = Pt(50)
        section.top_margin = section.bottom_margin = Pt(40)

    # Header
    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = name.add_run(profile.name)
    r.bold = True
    r.font.size = Pt(18)
    contact = doc.add_paragraph(
        " · ".join(
            [
                profile.location,
                profile.email,
                *(profile.phone and [profile.phone] or []),
                *profile.links.values(),
            ]
        )
    )
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Summary
    _heading(doc, titles["summary"])
    doc.add_paragraph(cv.summary.text)

    # Entries grouped by kind, keeping the relevance order chosen by the agent
    for kind in ("experience", "project", "education", "certificate"):
        entries = [(e, profile.item(e.item_id)) for e in cv.entries]
        entries = [(e, it) for e, it in entries if it and it.kind == kind]
        if not entries:
            continue
        _heading(doc, titles[kind])
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

    # Skills
    if cv.skills:
        _heading(doc, titles["skills"])
        doc.add_paragraph(", ".join(cv.skills))

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{date.today():%Y%m%d}_{_slug(posting.company)}_{_slug(posting.title)}.docx"
    path = settings.output_dir / fname
    doc.save(path)
    return path
