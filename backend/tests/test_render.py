from docx import Document

from app.profile import load_profile
from app.render import render_cover_letter, render_cv
from tests.fakes import good_cv, good_letter, posting


def _text(path) -> str:
    return "\n".join(p.text for p in Document(path).paragraphs)


def test_cv_docx_contains_name_and_bullets(tmp_path):
    path = render_cv(load_profile(), good_cv(), posting(), tmp_path)

    text = _text(path)
    assert path.parent == tmp_path
    assert "Alex Example" in text
    assert "Built a FastAPI backend serving device status to a dashboard." in text
    assert "Home Network Monitor" in text


def test_section_titles_follow_language(tmp_path):
    text = _text(render_cv(load_profile(), good_cv(), posting(language="es"), tmp_path))
    assert "EXPERIENCIA" in text
    assert "PROYECTOS" in text


def test_cover_letter_docx_has_greeting_paragraphs_and_signature(tmp_path):
    path = render_cover_letter(load_profile(), good_letter(), posting(), tmp_path)

    text = _text(path)
    greeting = next(line for line in text.splitlines() if line.startswith("Dear"))
    assert path.name != "cv.docx"
    assert "Acme" in greeting
    assert "I built a FastAPI backend for a home network monitor." in text
    assert text.rstrip().endswith("Alex Example")


def test_cover_letter_greeting_follows_language(tmp_path):
    text = _text(
        render_cover_letter(load_profile(), good_letter(), posting(language="es"), tmp_path)
    )
    assert "Estimado equipo de Acme" in text


def test_contact_line_skips_missing_fields(tmp_path):
    profile = load_profile().model_copy(update={"email": "", "location": "", "links": {}})
    lines = _text(render_cv(profile, good_cv(), posting(), tmp_path)).splitlines()
    assert lines[1] == ""  # nothing to show, and no stray separators
