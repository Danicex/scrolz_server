import os

from sqlmodel import Session, select
from model import Project, User, Chunk


# ---------- user ----------
def create_user(session: Session, email: str):
    user = User(email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user(session: Session, user_id: int):
    return session.get(User, user_id)


# ---------- project ----------
# crud.py



def create_project(session: Session, title: str, json_path: str, user_id: int) -> Project:
    project = Project(title=title, json_path=json_path, user_id=user_id)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def insert_chunks(session: Session, project_id: int, chunks: dict) -> int:
    """
    chunks = the dict loaded from json_path:
      { "chunk_1": {"text": ..., "summarized_text": ..., "quiz": [...], "audio": ..., "project_name": ...}, ... }
    """
    # idempotency: skip if already inserted
    existing = session.exec(
        select(Chunk).where(Chunk.project_id == project_id)
    ).first()
    if existing:
        return 0

    count = 0
    for idx, (key, chunk) in enumerate(chunks.items(), start=1):
        session.add(Chunk(
            project_id=project_id,
            index=idx,
            key=key,
            text=chunk.get("text", ""),
            summarized_text=chunk.get("summarized_text"),
            audio=chunk.get("audio"),
            quiz=chunk.get("quiz", []),
            project_name=chunk.get("project_name"),
        ))
        count += 1

    session.commit()
    return count


def get_project(session: Session, project_id: int):
    return session.get(Project, project_id)


def list_projects(session: Session, user_id: int):
    return session.exec(select(Project).where(Project.user_id == user_id)).all()


def update_project(session: Session, project_id: int, title: str):
    project = session.get(Project, project_id)
    if not project:
        return None
    project.title = title
    project.updated_at = now()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def delete_project(session: Session, project_id: int):
    project = session.get(Project, project_id)
    if not project:
        return False
    if os.path.exists(project.json_path):
        os.remove(project.json_path)
    session.delete(project)
    session.commit()
    return True
