from datetime import date, timedelta
from typing import Annotated

from fastapi import FastAPI, Depends, Path, Query, Body, APIRouter
from sqlmodel import Session, SQLModel, create_engine, Field, select, func
from starlette.exceptions import HTTPException

from ..dependencies import SessionDep
from ..models import Sesh, SeshType, SeshCreate, SeshBase, SeshUpdate, UserInDB
from .users import get_current_user


router = APIRouter(tags=["crud"])



@router.get("/seshs/")
def read_seshs(session: SessionDep):
    seshs = session.exec(select(Sesh)).all()
    return seshs


@router.post("/seshs/")
def create_seshs(session: SessionDep, current_user: Annotated[UserInDB, Depends(get_current_user)],
                 sesh_length: int, sesh_desc: str = "desc",  # i COULD add annotation with restrictions here # todoooooooooooooooo
                 sesh_type: SeshType = "programming",
                 sesh_day: date = date.today()):
    db_sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=current_user.id)
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


@router.delete("/seshs/")
def delete_seshs(session: SessionDep, sesh_id: int):
    sesh = session.get(Sesh, sesh_id)
    if not sesh:
        print("FUCKING KILL YOUSEFL")
        raise HTTPException(status_code=404, detail="FUCKING KILL YOURSELF")
    session.delete(sesh)
    session.commit()
    return {"msg": "fuck off aye"}


@router.put("/seshs/")
def update_sesh(session: SessionDep, sesh: SeshUpdate, sesh_id: int):
    db_sesh = session.get(Sesh, sesh_id)
    if not db_sesh:
        raise HTTPException(status_code=404, detail="nope mate")
    sesh_data = sesh.model_dump(exclude_unset=True)
    db_sesh.sqlmodel_update(sesh_data)
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


