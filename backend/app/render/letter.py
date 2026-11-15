"""Render a CoverLetter to .docx. Greeting and sign-off are added here, not by the LLM."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx.shared import Pt

from app.render.common import contact_header, new_document, save
from app.schemas import CoverLetter, JobPosting, Profile

GREETING = {
    "en": "Dear {company} hiring team,",
    "es": "Estimado equipo de {company}:",
    "ca": "Benvolgut equip de {company}:",
}
SIGN_OFF = {"en": "Kind regards,", "es": "Saludos cordiales,", "ca": "Salutacions cordials,"}


def render_cover_letter(
    profile: Profile, letter: CoverLetter, posting: JobPosting, out_dir: Path
) -> Path:
    lang = posting.language.value if posting.language.value in GREETING else "en"
    doc = new_document()
    contact_header(doc, profile)

    doc.add_paragraph(date.today().isoformat())
    doc.add_paragraph(GREETING[lang].format(company=posting.company))
    for line in letter.paragraphs:
        p = doc.add_paragraph(line.text)
        p.paragraph_format.space_after = Pt(8)
    doc.add_paragraph(SIGN_OFF[lang])
    doc.add_paragraph(profile.name)

    return save(doc, out_dir, "cover_letter.docx")
