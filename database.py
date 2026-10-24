from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from config import POSTGRES_URL
import model  # noqa: F401  (registers the tables)

engine = create_engine(POSTGRES_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


if __name__ == "__main__":
    create_db_and_tables()
