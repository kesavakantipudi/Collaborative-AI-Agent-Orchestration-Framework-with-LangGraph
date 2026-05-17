import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.api import router
from src.utils import redis_client

app = FastAPI(title="Collaborative AI Agent Orchestration API")
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/tasks/{task_id}")
async def ws_task_updates(websocket: WebSocket, task_id: str):
    await websocket.accept()
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = f"task:{task_id}:channel"
    pubsub.subscribe(channel)
    try:
        while True:
            message = pubsub.get_message(timeout=1.0)
            if message and message.get("type") == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pubsub.unsubscribe(channel)
        pubsub.close()
