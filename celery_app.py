from celery import Celery

# Use Redis as both broker and result backend
celery_app = Celery(
    "video_pipeline",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Optional: sensible defaults
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)