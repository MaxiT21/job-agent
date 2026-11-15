"""Thin LiteLLM wrapper: one function, any provider, always structured output.

Every call is recorded (step, model, latency, cost, ok):
- in the process-wide `usage` log (used by evals to compare providers);
- in every enclosing `track_usage()` block (the graph uses one per node for per-run usage).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field

import litellm
from pydantic import BaseModel, ValidationError

from app.config import settings

log = logging.getLogger(__name__)


@dataclass
class CallRecord:
    step: str
    model: str
    latency_s: float
    cost_usd: float | None
    ok: bool


@dataclass
class UsageLog:
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(c.cost_usd or 0 for c in self.calls)


usage = UsageLog()
_collectors: ContextVar[tuple[list[dict], ...]] = ContextVar("llm_usage_collectors", default=())


@contextmanager
def track_usage() -> Iterator[list[dict]]:
    """Collect the calls made inside the block as plain dicts (checkpoint-friendly).

    Blocks nest: a call is recorded in every enclosing block (e.g. per node and per eval).
    """
    calls: list[dict] = []
    token = _collectors.set((*_collectors.get(), calls))
    try:
        yield calls
    finally:
        _collectors.reset(token)


def record_call(record: CallRecord) -> None:
    usage.calls.append(record)
    for calls in _collectors.get():
        calls.append(asdict(record))


def structured[T: BaseModel](
    schema: type[T],
    *,
    system: str,
    user: str,
    step: str,
    model: str | None = None,
    retries: int = 1,
) -> T:
    """Call the LLM and parse its answer into `schema`. Retries once on bad JSON."""
    model = model or settings.model
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    for attempt in range(retries + 1):
        start = time.perf_counter()
        options = {"timeout": settings.llm_timeout_s, "num_retries": settings.llm_num_retries}
        if settings.llm_temperature is not None:
            options["temperature"] = settings.llm_temperature
        resp = litellm.completion(model=model, messages=messages, response_format=schema, **options)
        latency = round(time.perf_counter() - start, 3)
        try:
            cost = litellm.completion_cost(completion_response=resp)
        except Exception:  # unknown pricing for some models
            cost = None

        content = resp.choices[0].message.content
        try:
            result = schema.model_validate_json(content)
        except ValidationError as e:
            record_call(CallRecord(step, model, latency, cost, False))
            log.warning("Invalid %s output (attempt %s): %s", schema.__name__, attempt + 1, e)
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"That JSON was invalid: {e}. Return valid JSON only."},
            ]
            continue
        record_call(CallRecord(step, model, latency, cost, True))
        log.info("llm step=%s model=%s latency=%.2fs cost=%s", step, model, latency, cost)
        return result
    raise RuntimeError(f"{step}: model did not return a valid {schema.__name__}")
