"""Structured JSON logging for agent activity."""

import json
import logging
import os
from datetime import datetime, timezone

LOG_PATH = os.environ.get("AGENT_LOG_PATH", "/app/logs/agent_activity.log")


class JsonFileHandler(logging.Handler):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "task_id": getattr(record, "task_id", None),
            "agent_name": getattr(record, "agent_name", None),
            "action_details": record.getMessage(),
        }
        status = getattr(record, "status", None)
        if status:
            entry["status"] = status
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")


logger = logging.getLogger("agent_logger")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(JsonFileHandler(LOG_PATH))


def log_agent_action(
    task_id: str,
    agent_name: str,
    action_details: str,
    status: str | None = None,
) -> None:
    extra = {"task_id": task_id, "agent_name": agent_name}
    if status:
        extra["status"] = status
    logger.info(action_details, extra=extra)
