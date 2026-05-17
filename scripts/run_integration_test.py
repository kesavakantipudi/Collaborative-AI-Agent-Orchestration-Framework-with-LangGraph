#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8001")
TASK_PROMPT = os.environ.get(
    "INTEGRATION_PROMPT",
    "Research the key features of LangGraph and CrewAI. "
    "Write a short comparison summary for a technical audience.",
)
LOG_PATH = Path("logs/agent_activity.log")


def fail(message: str):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def api_post(path: str, payload: dict) -> dict:
    url = f"{API_URL}{path}"
    print(f"POST {url}")
    resp = httpx.post(url, json=payload, timeout=15.0)
    if resp.status_code >= 400:
        fail(f"POST {path} failed: {resp.status_code} {resp.text}")
    return resp.json()


def api_get(path: str) -> dict:
    url = f"{API_URL}{path}"
    print(f"GET {url}")
    resp = httpx.get(url, timeout=15.0)
    if resp.status_code >= 400:
        fail(f"GET {path} failed: {resp.status_code} {resp.text}")
    return resp.json()


def wait_for_status(task_id: str, target: str, timeout_seconds: int = 120) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        record = api_get(f"/api/v1/tasks/{task_id}")
        status = record.get("status")
        print(f"  current status: {status}")
        if status == target:
            return record
        time.sleep(2)
    fail(f"Task {task_id} did not reach status {target} within {timeout_seconds}s")


def find_log_entries(task_id: str) -> list[dict]:
    if not LOG_PATH.exists():
        fail(f"Agent log file not found: {LOG_PATH}")
    entries = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if task_id in line:
            try:
                payload = json.loads(line)
                entries.append(payload)
            except json.JSONDecodeError:
                continue
    return entries


def probe_redis_workspace(task_id: str) -> dict[str, str] | None:
    docker_commands = ["docker-compose", "docker compose"]
    workspace_key = f"task:{task_id}:workspace"
    field_names = ["research", "draft"]
    for base in docker_commands:
        for field in field_names:
            try:
                result = subprocess.run(
                    [base, "exec", "-T", "redis", "redis-cli", "--raw", "HGET", workspace_key, field],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).resolve().parent.parent,
                )
            except FileNotFoundError:
                break
            if result.returncode != 0:
                print(f"WARNING: redis workspace check failed with `{base}`: {result.stderr.strip()}")
                break
        else:
            workspace = {}
            for field in field_names:
                result = subprocess.run(
                    [base, "exec", "-T", "redis", "redis-cli", "--raw", "HGET", workspace_key, field],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).resolve().parent.parent,
                )
                if result.returncode == 0:
                    workspace[field] = result.stdout.rstrip("\n")
            return workspace
    print("WARNING: docker-compose not available; skipping Redis workspace validation")
    return None


def main() -> int:
    print("Integration test starting")
    print(f"API_URL={API_URL}")
    print(f"Prompt={TASK_PROMPT}")

    task_resp = api_post("/api/v1/tasks", {"prompt": TASK_PROMPT})
    task_id = task_resp.get("task_id")
    if not task_id:
        fail("Response did not include task_id")

    print(f"Created task: {task_id}")
    record = wait_for_status(task_id, "AWAITING_APPROVAL")
    print("Task reached AWAITING_APPROVAL")

    approve_resp = api_post(
        f"/api/v1/tasks/{task_id}/approve",
        {"approved": True, "feedback": "Integration test approval"},
    )
    print(f"Approve response: {approve_resp}")

    final_record = wait_for_status(task_id, "COMPLETED")
    print("Task reached COMPLETED")

    if not final_record.get("result"):
        fail("Completed task has empty result")
    if not isinstance(final_record.get("agent_logs"), list) or len(final_record["agent_logs"]) == 0:
        fail("agent_logs is missing or empty")
    agents_in_logs = {entry.get("agent", "") for entry in final_record["agent_logs"]}
    if not any("Research" in name for name in agents_in_logs):
        fail("agent_logs missing ResearchAgent entry")
    if not any("Writing" in name for name in agents_in_logs):
        fail("agent_logs missing WritingAgent entry")

    log_entries = find_log_entries(task_id)
    if not log_entries:
        fail(f"No agent activity log entries found for task {task_id}")
    print(f"Found {len(log_entries)} agent log entries in {LOG_PATH}")

    workspace = probe_redis_workspace(task_id)
    if workspace is not None:
        print(f"Redis workspace entries: {workspace}")

    print("Integration test succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
