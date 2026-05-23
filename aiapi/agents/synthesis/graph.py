from langgraph.graph import END, START, StateGraph

from .nodes import assess, cluster, compose, gather, quality_check, send_email_node, synthesise
from .state import SynthesisState


def _route_after_gather(state: SynthesisState) -> str:
    return END if not state["articles"] else "assess"


def _route_after_assess(state: SynthesisState) -> str:
    return END if state.get("skip_reason") else "cluster"


def _route_after_quality(state: SynthesisState) -> str:
    if state["quality_verdict"] in ("approved", "best_effort"):
        return "send_email"
    return "synthesise"


def build_synthesis_graph(checkpointer=None):
    g = StateGraph(SynthesisState)

    g.add_node("gather", gather)
    g.add_node("assess", assess)
    g.add_node("cluster", cluster)
    g.add_node("synthesise", synthesise)
    g.add_node("compose", compose)
    g.add_node("quality_check", quality_check)
    g.add_node("send_email", send_email_node)

    g.add_edge(START, "gather")
    g.add_conditional_edges("gather", _route_after_gather)
    g.add_conditional_edges("assess", _route_after_assess)
    g.add_edge("cluster", "synthesise")
    g.add_edge("synthesise", "compose")
    g.add_edge("compose", "quality_check")
    g.add_conditional_edges("quality_check", _route_after_quality)
    g.add_edge("send_email", END)

    return g.compile(checkpointer=checkpointer)
