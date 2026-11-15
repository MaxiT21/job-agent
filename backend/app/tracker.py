"""Application tracker.

MVP: append to a local CSV. Week 3: swap for a Supabase `applications` table
(same function signature, so nothing else changes).
"""
import csv
from datetime import date
from pathlib import Path

from app.config import settings
from app.schemas import JobPosting

FIELDS = ["date", "company", "title", "location", "fit_score", "cv_path", "status"]


def log_application(posting: JobPosting, fit_score: float, cv_path: Path) -> None:
    path = settings.output_dir / "applications.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "date": date.today().isoformat(),
            "company": posting.company,
            "title": posting.title,
            "location": posting.location or "",
            "fit_score": fit_score,
            "cv_path": str(cv_path),
            "status": "Ready to send",
        })
