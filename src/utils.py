import os
import json
import redis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def workspace_key(task_id: str) -> str:
    return f"task:{task_id}:workspace"


def publish_status(task_id: str, status: str):
    channel = f"task:{task_id}:channel"
    payload = json.dumps({"task_id": task_id, "status": status})
    redis_client.publish(channel, payload)
