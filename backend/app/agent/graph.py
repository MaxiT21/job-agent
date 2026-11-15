"""LangGraph wiring.

Fixed pipeline where steps are predictable, conditional edges where the agent
has to decide (vague posting, low fit, failed verification, user edits).

    fetch -> extract -> [vague?] -> ask_clarification -> extract
                     -> match -> [low fit?] -> confirm_low_fit -> END (stopped)
                              -> tailor_cv -> cover_letter -> verify
                                 verify -> [failed & retries left] -> tailor_cv
                                        -> human_approval -> [approved] -> render_and_log -> END
                                                          -> [edits]    -> tailor_cv
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from app import schemas
from app.agent import nodes
from app.agent.state import AgentState
from app.config import settings


def after_extract(state: AgentState) -> str:
    return "ask_clarification" if state["posting"].is_vague else "match_profile"


def after_match(state: AgentState) -> str:
    return "confirm_low_fit" if state["fit"].score < settings.low_fit_threshold else "tailor_cv"


def after_low_fit(state: AgentState) -> str:
    return END if state.get("status") == "stopped" else "tailor_cv"


def after_verify(state: AgentState) -> str:
    v = state["verification"]
    if not v.passed and state.get("verify_attempts", 0) <= settings.max_verify_retries:
        return "tailor_cv"
    return "human_approval"  # if still failing, the user sees the issues and decides


def after_approval(state: AgentState) -> str:
    return "render_and_log" if state.get("status") == "approved" else "tailor_cv"


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("fetch_posting", nodes.fetch_posting)
    g.add_node("extract_requirements", nodes.extract_requirements)
    g.add_node("ask_clarification", nodes.ask_clarification)
    g.add_node("match_profile", nodes.match_profile)
    g.add_node("confirm_low_fit", nodes.confirm_low_fit)
    g.add_node("tailor_cv", nodes.tailor_cv)
    g.add_node("write_cover_letter", nodes.write_cover_letter)
    g.add_node("verify", nodes.verify)
    g.add_node("human_approval", nodes.human_approval)
    g.add_node("render_and_log", nodes.render_and_log)

    g.add_edge(START, "fetch_posting")
    g.add_edge("fetch_posting", "extract_requirements")
    g.add_conditional_edges("extract_requirements", after_extract)
    g.add_edge("ask_clarification", "extract_requirements")
    g.add_conditional_edges("match_profile", after_match)
    g.add_conditional_edges("confirm_low_fit", after_low_fit)
    g.add_edge("tailor_cv", "write_cover_letter")
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
