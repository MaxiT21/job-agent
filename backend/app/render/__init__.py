"""Render approved documents to ATS-friendly .docx files (single column, no tables)."""

from app.render.common import run_output_dir
from app.render.cv import render_cv
from app.render.letter import render_cover_letter

__all__ = ["render_cover_letter", "render_cv", "run_output_dir"]
