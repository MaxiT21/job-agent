# Evals

## Dataset (`dataset/postings.jsonl`)
20–30 real postings, one JSON per line, labelled by hand:

```json
{"id": "p01", "source_url": "...", "text": "...",
 "gold_requirements": [{"text": "Python", "importance": "must"}],
 "gold_fit": "high|medium|low"}
```
Postings are public; keep anything private in `dataset/private/` (gitignored).

## Metrics
| Metric | How | Target |
|---|---|---|
| Extraction precision / recall | extracted vs gold requirements (fuzzy match) | > 0.85 |
| Hallucination rate | lines flagged by an independent fact-check model + manual spot-check | 0% |
| Fit agreement | agent score bucket vs `gold_fit` | > 80% |
| Cost / latency per run | from `app.llm.usage` | report per model |

## Run
```bash
python evals/run_evals.py --model gpt-4o-mini --model gemini/<model>
```
Output: a markdown table to paste into the main README.
