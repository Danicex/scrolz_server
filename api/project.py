import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import crud
from database import SessionDep
from task.task import run_video_pipeline, run_process_pdf
from task.task_status import init_task
import os

from celery_app import celery_app
from redis import redis_client
from datetime import datetime

from config import PROCESS_PDF_DIR

import shutil
from pathlib import Path
router = APIRouter(prefix="/project", tags=["scrolz-api"])



@router.post("/upload_pdf")
def upload_pdf(
    session: SessionDep,
    user_id: int = Form(...),
    file: UploadFile = File(...),
):
    if not crud.get_user(session, user_id):
        raise HTTPException(404, "User not found")

    os.makedirs(PROCESS_PDF_DIR, exist_ok=True)
    pdf_path = os.path.join(PROCESS_PDF_DIR, Path(file.filename).name)
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

   
    # Fire the task, then write its Redis record with the same id
    task = run_process_pdf.delay(pdf_path, file.filename, user_id)
    init_task(task.id, task_type="process_pdf", project_name=file.filename, user_id=user_id)

    return {"task_id": task.id, "status": "pending"}


@router.get("/")
def list_projects(session: SessionDep, user_id: int):
    return crud.list_projects(session, user_id)


@router.get("/{project_id}")
def get_project(session: SessionDep, project_id: int):
    project = crud.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/{project_id}/content")
def get_project_content(session: SessionDep, project_id: int):
    """The chunks json: text, summary, quiz and audio path per chunk."""
    project = crud.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    with open(project.json_path) as f:
        return json.load(f)


@router.patch("/{project_id}")
def update_project(session: SessionDep, project_id: int, title: str):
    project = crud.update_project(session, project_id, title)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(session: SessionDep, project_id: int):
    if not crud.delete_project(session, project_id):
        raise HTTPException(404, "Project not found")
    return {"deleted": project_id}
