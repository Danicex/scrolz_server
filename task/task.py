import json
import logging

from celery_app import celery_app
from create_video.compile_video import compile_video
from utils.process_pdf import process_pdf, json_to_db
from redis import redis_client
from task_status import update_task, init_task, get_task

log = logging.getLogger(__name__)
TASK_PREFIX = "task:"


# ---------- Stage 1 ----------

@celery_app.task(bind=True)
def run_process_pdf(self, pdf_path: str, filename: str, user_id: int):
    task_id = self.request.id
    update_task(task_id, status="started")

    try:
        # process_pdf returns {"title", "json_path", "cover", "images", "project_id", ...}
        result = process_pdf(pdf_path, filename, user_id)
    except Exception as e:
        update_task(task_id, status="failure", error=str(e))
        raise

    # persist the output the video pipeline needs
    update_task(
        task_id,
        status="success",
        json_path=result["json_path"],
        project_id=result["project_id"],
        project_name=result.get("title", filename),
    )

    # kick off stage 2 — the video task reads json_path from Redis itself
    run_video_pipeline.delay(task_id)   # pass the *task_id*, not the path
    return result


# ---------- Stage 2 ----------

@celery_app.task(bind=True)
def run_video_pipeline(self, source_task_id: str):
    """Reads json_path from the process_pdf task record, then compiles."""
    source = get_task(source_task_id)
    if not source or not source.get("json_path"):
        raise ValueError(f"No json_path for task {source_task_id}")

    json_path = source["json_path"]
    task_id = self.request.id
    init_task(
        task_id,
        task_type="video_pipeline",
        json_path=json_path,
        project_id=source.get("project_id"),
        project_name=source.get("project_name"),
    )
    update_task(task_id, status="started")

    try:
        result = compile_video(json_path)
    except Exception as e:
        update_task(task_id, status="failure", error=str(e))
        raise

    update_task(task_id, status="success", result=result)
    return result


# ---------- Watcher ----------

def iter_tasks():
    for key in redis_client.scan_iter(match=f"{TASK_PREFIX}*"):
        raw = redis_client.get(key)
        if not raw:
            continue
        try:
            yield key, json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Bad JSON in %s, skipping", key)


@celery_app.task
def scan_completed_tasks():
    for key, data in iter_tasks():
        if data.get("status") != "success":
            continue
        if data.get("task_type") != "process_pdf":
            continue

        # atomic claim so two beats don't double-run
        if not redis_client.set(f"lock:{key}", "1", nx=True, ex=60):
            continue

        try:
            json_to_db(data["json_path"], data["project_id"])
        except Exception:
            log.exception("json_to_db failed for %s", key)
            update_task(key.removeprefix(TASK_PREFIX), status="followup_failed")
            redis_client.delete(f"lock:{key}")
            continue

        redis_client.delete(key)
        redis_client.delete(f"lock:{key}")
        log.info("Migrated and dropped %s", key)


celery_app.conf.beat_schedule = {
    "scan-completed-tasks": {
        "task": "tasks.scan_completed_tasks",
        "schedule": 5.0,
    },
}