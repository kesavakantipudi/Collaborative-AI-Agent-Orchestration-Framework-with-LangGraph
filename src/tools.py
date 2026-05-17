"""Agent tools including a flaky web search for resilience testing."""

from src.logging_setup import log_agent_action
from src.utils import redis_client

FLAKY_QUERY = "__FLAKY_TEST__"

SEARCH_KNOWLEDGE = {
    "langgraph": (
        "LangGraph key features: stateful graph orchestration, cyclic workflows, "
        "checkpointing, human-in-the-loop interrupts, and tight LangChain integration."
    ),
    "crewai": (
        "CrewAI key features: role-based agents, task delegation, crew orchestration, "
        "tool integration, and production-oriented multi-agent pipelines."
    ),
}


def web_search(query: str, task_id: str) -> str:
    """Mock web search. Fails once for the flaky test query, then succeeds on retry."""
    log_agent_action(
        task_id,
        "ResearchAgent",
        f"Starting web search for '{query}'",
    )

    if query.strip() == FLAKY_QUERY:
        attempt_key = f"task:{task_id}:flaky_search_attempts"
        attempts = redis_client.incr(attempt_key)
        if attempts == 1:
            log_agent_action(
                task_id,
                "ResearchAgent",
                f"Web search failed for '{query}'",
                status="tool_error",
            )
            raise RuntimeError("simulated flaky tool failure on first attempt")

    q = query.lower()
    if "langgraph" in q:
        return SEARCH_KNOWLEDGE["langgraph"]
    if "crewai" in q or "crew ai" in q:
        return SEARCH_KNOWLEDGE["crewai"]
    if query.strip() == FLAKY_QUERY:
        return (
            "Flaky test recovery: LangGraph and CrewAI both support multi-agent "
            "orchestration with different ergonomics."
        )
    return f"Generic search results for: {query}"
