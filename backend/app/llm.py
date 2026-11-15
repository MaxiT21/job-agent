"""Thin LiteLLM wrapper: one function, any provider, always structured output.

Every call is logged with model, latency and cost so evals can compare providers.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from app.config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


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


def structured(
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
        resp = litellm.completion(
            model=model, messages=messages, response_format=schema, temperature=0
        )
        latency = time.perf_counter() - start
        try:
            cost = litellm.completion_cost(completion_response=resp)
        except Exception:  # unknown pricing for some models
            cost = None

        content = resp.choices[0].message.content
        try:
            result = schema.model_validate_json(content)
            usage.calls.append(CallRecord(step, model, latency, cost, True))
            return result
        except ValidationError as e:
            usage.calls.append(CallRecord(step, model, latency, cost, False))
            log.warning("Invalid %s output (attempt %s): %s", schema.__name__, attempt + 1, e)
            messages += [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"That JSON was invalid: {e}. Return valid JSON only."},
            ]
    raise RuntimeError(f"{step}: model did not return a valid {schema.__name__}")
