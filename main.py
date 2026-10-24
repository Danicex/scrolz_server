from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import project, user
from database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()  # runs once when the app starts
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(user.router)
app.include_router(project.router)

# run: uvicorn main:app --reload
