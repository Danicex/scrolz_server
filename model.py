from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON, Relationship, UniqueConstraint



def now():
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"  # "user" is a reserved word in Postgres

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=now)


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    json_path: str
    user_id: int = Field(foreign_key="users.id", index=True)
    cover: Optional[str] = None

    chunks: List["Chunk"] = Relationship(back_populates="project")


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("project_id", "index", name="uq_chunk_project_index"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="projects.id", index=True)
    index: int                              # 1-based, matches "chunk_1", "chunk_2"
    key: str                                # "chunk_1", "chunk_2", …
    text: str
    summarized_text: Optional[str] = None
    audio: Optional[str] = None             # path/URL to the mp3
    quiz: List[dict] = Field(default_factory=list, sa_column=Column(JSON))
    project_name: Optional[str] = None      # duplicated from Project for easy lookups

    project: Optional[Project] = Relationship(back_populates="chunks")
