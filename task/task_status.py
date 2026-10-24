import json
from datetime import datetime, timezone
from redis import redis_client

TTL = 60 * 60 * 24  # 24h


def init_task(task_id: str, task_type: str, **fields):
    """Called by the API — creates the key with status='pending'."""
    payload = {
        "task_type": task_type,
        "status": "pending",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "json_path": "",
        "project_id": None,
        "project_name": "",
        **fields,
    }
    redis_client.set(f"task:{task_id}", json.dumps(payload), ex=TTL)


def update_task(task_id: str, **fields):
    """Merge fields into an existing task record."""
    key = f"task:{task_id}"
    raw = redis_client.get(key)
    data = json.loads(raw) if raw else {}
    data.update(fields)
    redis_client.set(key, json.dumps(data), ex=TTL)


def get_task(task_id: str) -> dict | None:
    raw = redis_client.get(f"task:{task_id}")
    return json.loads(raw) if raw else None