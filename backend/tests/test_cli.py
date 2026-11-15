import io
from pathlib import Path

from app import cli
from app.agent.graph import build_graph
from tests.fakes import happy_script, match, posting

TEXT = "We need a Python + SQL intern. Kubernetes is a plus."


def run_cli(argv, answers, graph):
    out = io.StringIO()
    inputs = iter(answers)
    code = cli.main(argv, input_fn=lambda prompt="": next(inputs), out=out, graph=graph)
    return code, out.getvalue()


def test_full_run_with_approval(fake_llm):
    fake_llm(happy_script())

    code, out = run_cli(["run", "--text", TEXT], ["y"], build_graph())

    assert code == 0
    assert "Fit score: 80.0" in out
    assert "r3" in out and "gap" in out
    assert "Built a FastAPI backend serving device status to a dashboard." in out
    assert "Status: done" in out
    cv_line = next(line for line in out.splitlines() if line.strip().startswith("CV:"))
    assert Path(cv_line.split("CV:")[1].strip()).exists()


def test_edit_then_approve(fake_llm):
    llm = fake_llm(happy_script())

    code, out = run_cli(["run", "--text", TEXT], ["e", "Mention SQL first", "y"], build_graph())

    assert code == 0
    assert "Mention SQL first" in llm.prompts("tailor_cv")[-1]
    assert "Status: done" in out


def test_vague_posting_then_low_fit_stop(fake_llm):
    fake_llm(
        happy_script(extract=[posting(vague=True), posting()], match=[match("gap", "gap", "gap")])
    )

    code, out = run_cli(["run", "--text", TEXT], ["Python backend", "n"], build_graph())

    assert code == 0
    assert "What stack does the team use?" in out
    assert "Fit score: 0.0" in out
    assert "Status: stopped" in out


def test_reads_posting_from_file(tmp_path, fake_llm):
    llm = fake_llm(happy_script())
    f = tmp_path / "posting.txt"
    f.write_text(TEXT)

    run_cli(["run", "--file", str(f)], ["y"], build_graph())

    assert TEXT in llm.prompts("extract")[0]


def test_provider_error_exits_non_zero_with_retry_hint(fake_llm):
    fake_llm(happy_script(match=[RuntimeError("Gemini 503: overloaded")]))

    code, out = run_cli(["run", "--text", TEXT], [], build_graph())

    assert code == 1
    assert "overloaded" in out
    assert "resume" in out


def test_resume_retries_a_failed_run(fake_llm):
    fake_llm(happy_script(match=[RuntimeError("Gemini 503"), match("met", "met", "gap")]))
    graph = build_graph()
    _, out = run_cli(["run", "--text", TEXT], [], graph)
    run_id = next(line for line in out.splitlines() if line.startswith("Run id:")).split()[-1]

    code, out = run_cli(["resume", run_id], ["y"], graph)

    assert code == 0
    assert "Status: done" in out


def test_resume_unknown_run(fake_llm):
    code, out = run_cli(["resume", "nope"], [], build_graph())
    assert code == 1
    assert "No run" in out
