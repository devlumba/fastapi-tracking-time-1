from typing import Annotated
from datetime import date, timedelta

from fastapi import FastAPI, Depends, Path
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, Field, select
from enum import Enum
from starlette.exceptions import HTTPException


class SeshType(Enum):
    duolingo = "duolingo"
    programming = "programming"


class SeshBase(SQLModel):
    type: SeshType | None = Field(index=True, default=None)
    length: int | None = Field(default=None, index=True)
    specifics: str = Field()
    day: date = Field(index=True)


class Sesh(SeshBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class SeshCreate(SeshBase):
    pass



sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


app = FastAPI(
    title="tracking sesh's",
    summary="larping it rn",
    version="1.6.7",
)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/seshs/")
def read_seshs(session: SessionDep):
    seshs = session.exec(select(Sesh)).all()
    return seshs


@app.post("/seshs/")
def create_seshs(sesh: SeshCreate, sesh_type:SeshType, session: SessionDep):
    db_sesh = Sesh.model_validate(sesh)
    db_sesh.type = sesh_type
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


@app.delete("/seshs/")
def delete_seshs(session: SessionDep, sesh_id: int):
    sesh = session.get(Sesh, sesh_id)
    if not sesh:
        print("FUCKING KILL YOUSEFL")
        raise HTTPException(status_code=404, detail="FUCKING KILL YOURSELF")
    session.delete(sesh)
    session.commit()
    return {"msg": "fuck off aye"}


# basic routes done


@app.get("/seshs/programming/") # could be read_type but it's just 2
def read_seshs_programming(session: SessionDep):
    seshs = session.exec(select(Sesh).where(Sesh.type == "programming")).all()
    return seshs


@app.get("/seshs/duolingo/") # could be read_type but it's just 2
def read_seshs_duolingo(session: SessionDep):
    seshs = session.exec(select(Sesh).where(Sesh.type == "duolingo")).all()
    return seshs


# @app.get("/seshs/{age}")
# def read_seshs_age_alt(age: int, session: SessionDep):
#     example_day = date.today()
#     seshs_all = session.exec(select(Sesh)).all()
#     seshs = []
#     for i in seshs_all:
#         if example_day - i.day <= timedelta(days=age):
#             seshs.append(i)
#     return seshs


@app.get("/seshs/{age}")
def read_seshs_age(age: int, session: SessionDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.day >= cutoff_day)).all()
    return seshs


@app.get("/seshs/{age}/time")
def read_time_age(sesh_type: SeshType, age: int, session: SessionDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.type == sesh_type, Sesh.day >= cutoff_day)).all()
    sum = 0
    for i in seshs:
        sum += i.length
    return {"minutes": sum, "hours": sum/60}

