#!/usr/bin/env python3
"""Listen for task status updates on /ws/tasks/{task_id}."""

import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Install dependency: pip install websockets", file=sys.stderr)
    raise SystemExit(1)


async def listen(task_id: str, base_url: str) -> None:
    uri = f"{base_url.rstrip('/')}/ws/tasks/{task_id}"
    print(f"Connecting to {uri}")
    async with websockets.connect(uri) as ws:
        print("Connected. Waiting for status messages (Ctrl+C to exit)...")
        while True:
            message = await ws.recv()
            try:
                payload = json.loads(message)
                print(json.dumps(payload, indent=2))
            except json.JSONDecodeError:
                print(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="WebSocket listener for task updates")
    parser.add_argument("task_id", help="Task UUID from POST /api/v1/tasks")
    parser.add_argument(
        "--url",
        default="ws://localhost:8001",
        help="WebSocket base URL (default: ws://localhost:8001)",
    )
    args = parser.parse_args()
    asyncio.run(listen(args.task_id, args.url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
