import pytest

from app import tracker
from tests.fakes import posting


def test_logged_application_is_listed_newest_first():
    tracker.log_application("run-1", posting(), 70.0, "/o/1/cv.docx", None)
    tracker.log_application("run-2", posting(), 80.0, "/o/2/cv.docx", "/o/2/cover_letter.docx")

    apps = tracker.list_applications()
    assert [a.run_id for a in apps] == ["run-2", "run-1"]
    assert apps[0].company == "Acme"
    assert apps[0].status == "ready"
    assert apps[1].letter_path is None


def test_logging_the_same_run_twice_keeps_one_row():
    tracker.log_application("run-1", posting(), 70.0, "/o/1/cv.docx", None)
    tracker.log_application("run-1", posting(), 75.0, "/o/1/cv.docx", None)

    apps = tracker.list_applications()
    assert len(apps) == 1
    assert apps[0].fit_score == 75.0


def test_update_status():
    tracker.log_application("run-1", posting(), 70.0, "/o/1/cv.docx", None)

    updated = tracker.update_status("run-1", "interview")

    assert updated.status == "interview"
    assert tracker.list_applications()[0].status == "interview"


def test_update_status_of_unknown_run_raises():
    with pytest.raises(KeyError):
        tracker.update_status("missing", "applied")
