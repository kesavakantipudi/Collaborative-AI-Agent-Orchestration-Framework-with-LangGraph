import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.db import init_db, SessionLocal
from src import worker_tasks
from src.utils import publish_status
from sqlalchemy import text

router = APIRouter()


class CreateTaskRequest(BaseModel):
    prompt: str


@router.on_event("startup")
def startup():
    init_db()


@router.post("/tasks", status_code=202)
def create_task(req: CreateTaskRequest):
    db = SessionLocal()
    task_id = str(uuid.uuid4())
    db.execute(text("INSERT INTO tasks (id, prompt, status, created_at, updated_at) VALUES (:id, :prompt, :status, NOW(), NOW())"), {"id": task_id, "prompt": req.prompt, "status": 'PENDING'})
    db.commit()
    # enqueue background work
    worker_tasks.start_workflow.delay(task_id, req.prompt)
    return {"task_id": task_id, "status": "PENDING"}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    db = SessionLocal()
    row = db.execute(text("SELECT id, prompt, status, result, agent_logs, created_at, updated_at FROM tasks WHERE id=:id"), {"id": task_id}).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    res = dict(row)
    # serialize timestamps
    for t in ("created_at", "updated_at"):
        if res.get(t) is not None:
            try:
                res[t] = res[t].isoformat()
            except Exception:
                res[t] = str(res[t])
    # ensure agent_logs is JSON
    if res.get('agent_logs') and isinstance(res['agent_logs'], str):
        try:
            res['agent_logs'] = json.loads(res['agent_logs'])
        except Exception:
            pass
    return res


class ApproveRequest(BaseModel):
    approved: bool
    feedback: str | None = None


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: str, req: ApproveRequest):
    db = SessionLocal()
    row = db.execute(text("SELECT id FROM tasks WHERE id=:id"), {"id": task_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    if not req.approved:
        db.execute(
            text("UPDATE tasks SET status=:status, updated_at=NOW() WHERE id=:id"),
            {"status": "FAILED", "id": task_id},
        )
        db.commit()
        publish_status(task_id, "FAILED")
        return {"task_id": task_id, "status": "FAILED"}

    db.execute(
        text("UPDATE tasks SET status=:status, updated_at=NOW() WHERE id=:id"),
        {"status": "RESUMED", "id": task_id},
    )
    db.commit()
    publish_status(task_id, "RESUMED")
    return {"task_id": task_id, "status": "RESUMED"}
