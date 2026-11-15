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
The metric functions and the runner itself are tested offline (`backend/tests/test_eval_metrics.py`).
