"""LangGraph wiring.

Fixed pipeline where steps are predictable, conditional edges where the agent
has to decide (vague posting, low fit, failed verification, user edits).

    fetch -> extract -> [vague?] -> ask_clarification -> extract
                     -> match -> [low fit?] -> confirm_low_fit -> END (stopped)
                              -> tailor_cv -> cover_letter -> verify
                                 verify -> [failed & retries left] -> tailor_cv and/or cover_letter
                                           (only the document(s) with issues are regenerated)
                                        -> human_approval -> [approved] -> render_and_log -> END
                                                          -> [edits]    -> tailor_cv -> cover_letter

Every node is wrapped with `tracked()` so the LLM calls it makes are stored in the run's
state (`llm_calls`), which is how the API reports cost and latency per run.
"""

from collections.abc import Callable
from functools import wraps

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from app import schemas
from app.agent import nodes
from app.agent.state import AgentState
from app.config import settings
from app.llm import track_usage


def tracked(node: Callable[[AgentState], dict]) -> Callable[[AgentState], dict]:
    @wraps(node)
    def run(state: AgentState) -> dict:
        with track_usage() as calls:
            update = node(state)
        return {**update, "llm_calls": calls} if calls else update

    return run


def after_extract(state: AgentState) -> str:
    return "ask_clarification" if state["posting"].is_vague else "match_profile"


def after_match(state: AgentState) -> str:
    return "confirm_low_fit" if state["fit"].score < settings.low_fit_threshold else "tailor_cv"


def after_low_fit(state: AgentState) -> str:
    return END if state.get("status") == "stopped" else "tailor_cv"


def after_verify(state: AgentState) -> str:
    v = state["verification"]
    if not v.passed and state.get("verify_attempts", 0) <= settings.max_verify_retries:
        return "tailor_cv" if "cv" in state.get("regenerate", ["cv"]) else "write_cover_letter"
    return "human_approval"  # if still failing, the user sees the issues and decides


def after_tailor(state: AgentState) -> str:
    return "write_cover_letter" if "letter" in state.get("regenerate", ["letter"]) else "verify"


def after_approval(state: AgentState) -> str:
    return "render_and_log" if state.get("status") == "approved" else "tailor_cv"


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("fetch_posting", tracked(nodes.fetch_posting))
    g.add_node("extract_requirements", tracked(nodes.extract_requirements))
    g.add_node("ask_clarification", tracked(nodes.ask_clarification))
    g.add_node("match_profile", tracked(nodes.match_profile))
    g.add_node("confirm_low_fit", tracked(nodes.confirm_low_fit))
    g.add_node("tailor_cv", tracked(nodes.tailor_cv))
    g.add_node("write_cover_letter", tracked(nodes.write_cover_letter))
    g.add_node("verify", tracked(nodes.verify))
    g.add_node("human_approval", tracked(nodes.human_approval))
    g.add_node("render_and_log", tracked(nodes.render_and_log))

    g.add_edge(START, "fetch_posting")
    g.add_edge("fetch_posting", "extract_requirements")
    g.add_conditional_edges("extract_requirements", after_extract)
    g.add_edge("ask_clarification", "extract_requirements")
    g.add_conditional_edges("match_profile", after_match)
    g.add_conditional_edges("confirm_low_fit", after_low_fit)
    g.add_conditional_edges("tailor_cv", after_tailor)
    g.add_edge("write_cover_letter", "verify")
    g.add_conditional_edges("verify", after_verify)
    g.add_conditional_edges("human_approval", after_approval)
    g.add_edge("render_and_log", END)

    # MemorySaver is fine for dev; swap for a Postgres checkpointer (Supabase) in prod.
    return g.compile(checkpointer=checkpointer or MemorySaver(serde=_serializer()))


def _serializer() -> JsonPlusSerializer:
    """Explicitly allow our Pydantic state types to be restored from checkpoints."""
    allowed = [("app.schemas", name) for name in schemas.__all_state_types__]
    return JsonPlusSerializer(allowed_msgpack_modules=allowed)


graph = build_graph()
