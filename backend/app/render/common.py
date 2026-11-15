"""Shared .docx helpers and output locations."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.config import settings
from app.schemas import JobPosting, Profile

ACCENT = RGBColor(0x1F, 0x3A, 0x5F)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def run_output_dir(posting: JobPosting, run_id: str) -> Path:
    """One folder per run, so the same posting twice never overwrites earlier files."""
    name = f"{date.today():%Y%m%d}_{slug(posting.company)}_{slug(posting.title)}_{run_id[:8]}"
    return settings.output_dir / "runs" / name


def new_document() -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    for section in doc.sections:
        section.left_margin = section.right_margin = Pt(50)
        section.top_margin = section.bottom_margin = Pt(40)
    return doc


def contact_header(doc: Document, profile: Profile) -> None:
    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = name.add_run(profile.name)
    r.bold = True
    r.font.size = Pt(18)
    parts = [profile.location, profile.email, *([profile.phone] if profile.phone else [])]
    contact = doc.add_paragraph(" · ".join(p for p in [*parts, *profile.links.values()] if p))
    contact.alignment = WD_ALIGN_PARAGRAPH.CENTER


def heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = ACCENT


def save(doc: Document, out_dir: Path, filename: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    doc.save(path)
    return path
