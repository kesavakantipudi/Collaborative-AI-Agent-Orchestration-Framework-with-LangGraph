"""Specialized agents: ResearchAgent and WritingAgent with tool-backed logic."""

from src.logging_setup import log_agent_action
from src.tools import FLAKY_QUERY, web_search
from src.utils import redis_client, workspace_key


def run_research(task_id: str, prompt: str) -> str:
    """ResearchAgent gathers LangGraph and CrewAI feature information via tools."""
    log_agent_action(
        task_id,
        "ResearchAgent",
        f"Starting research for prompt: {prompt[:120]}",
    )

    if prompt.strip() == FLAKY_QUERY:
        findings = _research_with_retry(task_id, FLAKY_QUERY)
    else:
        langgraph_info = _research_with_retry(task_id, "LangGraph features")
        crewai_info = _research_with_retry(task_id, "CrewAI features")
        findings = f"{langgraph_info}\n\n{crewai_info}"

    redis_client.hset(workspace_key(task_id), mapping={"research": findings})
    log_agent_action(task_id, "ResearchAgent", "Research findings written to Redis workspace")
    return findings


def _research_with_retry(task_id: str, query: str, max_attempts: int = 2) -> str:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return web_search(query, task_id)
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                log_agent_action(
                    task_id,
                    "ResearchAgent",
                    f"Retrying web search for '{query}' (attempt {attempt + 1})",
                )
    raise last_error  # type: ignore[misc]


def run_writing(task_id: str) -> str:
    """WritingAgent reads research from Redis workspace and drafts a comparison."""
    research = redis_client.hget(workspace_key(task_id), "research")
    if not research:
        research = "No research data available in workspace."

    log_agent_action(
        task_id,
        "WritingAgent",
        "Reading research findings from Redis workspace",
    )

    draft = (
        "Technical comparison: LangGraph vs CrewAI\n\n"
        f"{research}\n\n"
        "Summary: LangGraph emphasizes graph-based state machines, checkpointing, "
        "and human-in-the-loop control for agent workflows. CrewAI emphasizes "
        "role-based crews, delegated tasks, and production-ready multi-agent "
        "coordination. Choose LangGraph when you need fine-grained graph control; "
        "choose CrewAI when you want higher-level crew abstractions for teams of agents."
    )

    redis_client.hset(workspace_key(task_id), mapping={"draft": draft})
    log_agent_action(task_id, "WritingAgent", "Draft comparison summary completed")
    return draft
