from fastapi import APIRouter

import crud
from database import SessionDep

router = APIRouter(prefix="/user", tags=["scrolz-api"])


@router.post("/")
def create_user(session: SessionDep, email: str):
    return crud.create_user(session, email)
