# Evals

Measure how well each model does the job, offline from the app, on a fixed dataset.

## Dataset (`dataset/postings.jsonl`)
Fictional postings (en / es / ca), one JSON per line, labelled by hand **against the sample profile** (`backend/data/profile.sample.yaml`):

```json
{"id": "p01", "lang": "en", "text": "...",
 "gold_requirements": [{"text": "Python", "importance": "must"}],
 "gold_fit": "high|medium|low|null", "gold_vague": false}
```
`gold_fit` buckets follow the app's score: low < 50 ≤ medium < 75 ≤ high.
Real postings or your real profile go in `dataset/private/` (gitignored).

## Metrics
| Metric | How | Target |
|---|---|---|
| Extraction precision / recall | extracted vs gold requirements (fuzzy match, `metrics.py`) | > 0.85 |
| Vague detection | `is_vague` vs `gold_vague` | all |
| Fit agreement | agent score bucket vs `gold_fit` | > 80% |
| First-pass verified (`--full`) | runs whose first draft passed both verifier layers | report |
| Residual flagged lines (`--full`) | lines still flagged after retries / all generated lines | 0% |
| Cost / latency | from the recorded LLM calls | report per model |

## Run
```bash
cd backend
uv run python ../evals/run_evals.py --model gemini/gemini-flash-latest
uv run python ../evals/run_evals.py --model gemini/gemini-flash-latest --model gpt-4o-mini --full
```
Needs the provider keys in `.env`. Output: a markdown table, also saved to `results/<date>_<models>.md`, ready to paste into the main README.
Runs go to a fresh temporary SQLite file, so evals never touch the app's database (`--db <file>` to keep them).
The metric functions, the threshold gate and the runner itself are tested offline (`backend/tests/test_eval_metrics.py`).

## Regression gate (CI)
```bash
uv run python ../evals/run_evals.py --model gemini/gemini-flash-latest --full --limit 4 \
  --min-recall 0.85 --max-residual 0
```
exits 1 if extraction recall drops below 0.85, if any unsupported line survives into the final documents, or if a case errors.
[`.github/workflows/evals.yml`](../.github/workflows/evals.yml) runs exactly this on every push or PR that touches the prompts, the agent, the verifier or the evals (and on demand), and writes the table to the job summary. It needs a `GEMINI_API_KEY` repository secret; without it the job skips itself. One run costs about $0.15.
