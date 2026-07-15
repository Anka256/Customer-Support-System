from langgraph.graph import END, StateGraph

from app.pipeline import nodes
from app.pipeline.state import TicketState, new_state


def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("validate", nodes.validate_node)
    graph.add_node("injection_check", nodes.injection_check_node)
    graph.add_node("language_detection", nodes.language_detection_node)
    graph.add_node("classify_and_draft", nodes.classify_and_draft_node)
    graph.add_node("confidence_eval", nodes.confidence_eval_node)
    graph.add_node("mark_auto_ready", nodes.mark_auto_ready_node)
    graph.add_node("mark_manual_review", nodes.mark_manual_review_node)
    graph.add_node("persist", nodes.persist_node)

    graph.set_entry_point("validate")

    # 1 -> 2: reject short-circuits straight to persist (logged, no ticket row)
    graph.add_conditional_edges(
        "validate",
        nodes.route_after_validate,
        {"rejected": "persist", "continue": "injection_check"},
    )

    # 2 -> 3: confirmed injection also short-circuits to persist
    graph.add_conditional_edges(
        "injection_check",
        nodes.route_after_injection_check,
        {"rejected": "persist", "continue": "language_detection"},
    )

    graph.add_edge("language_detection", "classify_and_draft")

    # 4 -> 5: if classification itself failed after retries, there's nothing
    # to judge — skip straight to manual_review
    graph.add_conditional_edges(
        "classify_and_draft",
        nodes.route_after_classify,
        {"failed": "mark_manual_review", "continue": "confidence_eval"},
    )

    # 6: the confidence router — the one required conditional edge that
    # decides auto_ready vs manual_review based on the judge's score
    graph.add_conditional_edges(
        "confidence_eval",
        nodes.route_by_confidence,
        {"auto_ready": "mark_auto_ready", "manual_review": "mark_manual_review"},
    )

    graph.add_edge("mark_auto_ready", "persist")
    graph.add_edge("mark_manual_review", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(raw_text: str) -> TicketState:
    """Synchronous entrypoint — runs the full pipeline for one ticket and
    returns the final state. Call this from a worker thread when invoked
    from async code (e.g. `await asyncio.to_thread(run_pipeline, text)`)."""
    graph = get_compiled_graph()
    state = new_state(raw_text)
    return graph.invoke(state)
