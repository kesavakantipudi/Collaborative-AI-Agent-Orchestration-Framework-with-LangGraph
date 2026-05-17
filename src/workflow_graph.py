"""LangGraph workflow: ResearchAgent -> WritingAgent -> human approval -> finalize."""

from __future__ import annotations

import json
import time
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src import agents
from src.db import SessionLocal
from src.logging_setup import log_agent_action
from src.utils import publish_status, redis_client, workspace_key
from sqlalchemy import text


class WorkflowState(TypedDict, total=False):
    task_id: str
    prompt: str
    research_findings: str
    draft: str
    agent_logs: list
    approved: bool
    feedback: str
    error: str


def _append_log(state: WorkflowState, agent: str, action: str) -> list:
    logs = list(state.get("agent_logs") or [])
    logs.append(
        {
            "agent": agent,
            "action": action,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    return logs


def _persist_logs(task_id: str, logs: list) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE tasks SET agent_logs=:logs, updated_at=NOW() WHERE id=:id"),
            {"logs": json.dumps(logs), "id": task_id},
        )
        db.commit()
    finally:
        db.close()


def research_node(state: WorkflowState) -> WorkflowState:
    task_id = state["task_id"]
    prompt = state["prompt"]
    log_agent_action(task_id, "ResearchAgent", "Searching for LangGraph features")
    findings = agents.run_research(task_id, prompt)
    logs = _append_log(state, "ResearchAgent", "Searching for LangGraph features")
    _persist_logs(task_id, logs)
    return {**state, "research_findings": findings, "agent_logs": logs}


def writing_node(state: WorkflowState) -> WorkflowState:
    task_id = state["task_id"]
    log_agent_action(task_id, "WritingAgent", "Drafting comparison summary")
    draft = agents.run_writing(task_id)
    logs = _append_log(state, "WritingAgent", "Drafting comparison summary")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE tasks SET agent_logs=:logs, status=:status, "
                "result=:result, updated_at=NOW() WHERE id=:id"
            ),
            {
                "logs": json.dumps(logs),
                "status": "AWAITING_APPROVAL",
                "result": draft,
                "id": task_id,
            },
        )
        db.commit()
    finally:
        db.close()
    publish_status(task_id, "AWAITING_APPROVAL")
    return {**state, "draft": draft, "agent_logs": logs}


def await_approval_node(state: WorkflowState) -> WorkflowState:
    """Poll database until human approves or rejects via the API."""
    task_id = state["task_id"]
    waited = 0
    timeout = 600
    while waited < timeout:
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT status FROM tasks WHERE id=:id"),
                {"id": task_id},
            ).mappings().fetchone()
        finally:
            db.close()
        if row and row["status"] == "RESUMED":
            publish_status(task_id, "RESUMED")
            return {**state, "approved": True}
        if row and row["status"] == "FAILED":
            return {**state, "approved": False, "error": "rejected by human reviewer"}
        time.sleep(2)
        waited += 2
    return {**state, "approved": False, "error": "approval timeout"}


def finalize_node(state: WorkflowState) -> WorkflowState:
    task_id = state["task_id"]
    if not state.get("approved"):
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE tasks SET status=:status, updated_at=NOW() WHERE id=:id"),
                {"status": "FAILED", "id": task_id},
            )
            db.commit()
        finally:
            db.close()
        publish_status(task_id, "FAILED")
        return state

    draft = state.get("draft") or redis_client.hget(workspace_key(task_id), "draft")
    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE tasks SET result=:result, status=:status, updated_at=NOW() "
                "WHERE id=:id"
            ),
            {"result": draft, "status": "COMPLETED", "id": task_id},
        )
        db.commit()
    finally:
        db.close()
    publish_status(task_id, "COMPLETED")
    log_agent_action(task_id, "Workflow", "Workflow completed successfully")
    return state


def build_workflow_graph():
    graph = StateGraph(WorkflowState)
    graph.add_node("research", research_node)
    graph.add_node("writing", writing_node)
    graph.add_node("await_approval", await_approval_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "writing")
    graph.add_edge("writing", "await_approval")
    graph.add_edge("await_approval", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


workflow_app = build_workflow_graph()
