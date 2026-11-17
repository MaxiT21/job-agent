# Eval results — 2026-11-17

8 cases, sample profile.

**Partial run:** the API's prepaid credits ran out at p06, so only p01–p05 completed (vague detection 6/8 counts the two that errored). Not directly comparable with the full runs.

| Model | Extraction P | Extraction R | Vague detection | Fit agreement | First-pass verified | Residual flagged lines | Avg verify attempts | Calls | Cost (USD) | Avg latency/call (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| gemini/gemini-3.1-pro-preview | 0.90 | 1.00 | 6/8 | 6/6 | 2/5 | 3/47 | 1.80 | 52 | 1.4529 | 14.1 |

## gemini/gemini-3.1-pro-preview
- error — p06: RuntimeError: litellm.PaymentRequiredError: GeminiException - {
  "error": {
    "code": 402,
    "message": "Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects to manage you
- error — p07: PaymentRequiredError: litellm.PaymentRequiredError: GeminiException - {
  "error": {
    "code": 402,
    "message": "Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects to manage you
- error — p08: PaymentRequiredError: litellm.PaymentRequiredError: GeminiException - {
  "error": {
    "code": 402,
    "message": "Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects to manage you
