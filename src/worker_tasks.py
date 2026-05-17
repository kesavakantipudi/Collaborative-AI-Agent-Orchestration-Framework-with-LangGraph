"""Celery tasks that execute the LangGraph multi-agent workflow."""

from src.celery_app import celery
from src.db import SessionLocal
from src.logging_setup import log_agent_action
from src.utils import publish_status
from src.workflow_graph import workflow_app
from sqlalchemy import text


@celery.task(bind=True, default_retry_delay=2, max_retries=2)
def start_workflow(self, task_id: str, prompt: str):
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE tasks SET status=:status, updated_at=NOW() WHERE id=:id"),
            {"status": "RUNNING", "id": task_id},
        )
        db.commit()
        publish_status(task_id, "RUNNING")
        log_agent_action(task_id, "Workflow", "LangGraph workflow started")

        initial_state = {
            "task_id": task_id,
            "prompt": prompt,
            "agent_logs": [],
        }
        workflow_app.invoke(initial_state)
    except Exception as exc:
        log_agent_action(
            task_id,
            "Workflow",
            f"Workflow failed: {exc}",
            status="error",
        )
        db.execute(
            text("UPDATE tasks SET status=:status, updated_at=NOW() WHERE id=:id"),
            {"status": "FAILED", "id": task_id},
        )
        db.commit()
        publish_status(task_id, "FAILED")
        raise
    finally:
        db.close()
