from typing import Annotated
from datetime import date, timedelta
import calendar

from fastapi import FastAPI, Depends, Path
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, Field, select, func
from enum import Enum
from starlette.exceptions import HTTPException

from dark_swag import FastAPI



class SeshType(Enum):
    duolingo = "duolingo"
    programming = "programming"
    words = "words"
    reading = "reading"
    juggling = "juggling"


class SeshBase(SQLModel):
    length: int | None = Field(default=None, index=True)
    specifics: str = Field()
    day: date = Field(index=True)


class Sesh(SeshBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: SeshType | None = Field(index=True, default=None)


class SeshCreate(SeshBase):
    pass


class SeshUpdate(SeshBase):
    length: int | None = None
    specifics: str | None = None
    day: date | None = None
    type: SeshType | None = None


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

templates = Jinja2Templates(directory="templates-hours")

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


@app.get("/")
def root():
    return RedirectResponse(url="/docs_light")


@app.get("/seshs/", tags=["crud"])
def read_seshs(session: SessionDep):
    seshs = session.exec(select(Sesh)).all()
    return seshs


@app.post("/seshs/", tags=["crud"])
def create_seshs(sesh: SeshCreate, sesh_type:SeshType, session: SessionDep):
    db_sesh = Sesh.model_validate(sesh)
    db_sesh.type = sesh_type
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


@app.delete("/seshs/", tags=["crud"])
def delete_seshs(session: SessionDep, sesh_id: int):
    sesh = session.get(Sesh, sesh_id)
    if not sesh:
        print("FUCKING KILL YOUSEFL")
        raise HTTPException(status_code=404, detail="FUCKING KILL YOURSELF")
    session.delete(sesh)
    session.commit()
    return {"msg": "fuck off aye"}


@app.put("/seshs/", tags=["crud"])
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


# basic routes done


@app.get("/seshs/programming/", tags=["programming"]) # could be read_type but it's just 2
def read_seshs_programming(session: SessionDep):
    seshs = session.exec(select(Sesh).where(Sesh.type == "programming")).all()
    return seshs


@app.get("/seshs/duolingo/", tags=["seshs_general"]) # could be read_type but it's just 2
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


@app.get("/seshs/time/{age}", tags=["seshs_general"])
def read_seshs_age(age: int, session: SessionDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.day >= cutoff_day)).all()
    return seshs


@app.get("/seshs/time/{age}/time", tags=["seshs_general"])
def read_time_age(sesh_type: SeshType, age: int, session: SessionDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.type == sesh_type, Sesh.day >= cutoff_day)).all()
    sum = 0
    for i in seshs:
        sum += i.length
    return {"minutes": sum, "hours": sum/60}


@app.get("/seshs/programming/week", tags=["programming"])
def read_seshs_programming_week(session: SessionDep):
    cutoff_date = date.today() - timedelta(days=6)
    time = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == SeshType.programming, Sesh.day >= cutoff_date)).one() or 0
    return {"minutes last week": time, "hours last week": time/60}


@app.get("/seshs/programming/fortnight", tags=["programming"])
def read_seshs_programming_fortnight(session: SessionDep):
    cutoff_date = date.today() - timedelta(days=13)
    time = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming", Sesh.day >= cutoff_date)).one() or 0
    return {"minutes last fortnight": time, "hours last fortnight": time/60}


@app.get("/seshs/programming/month", tags=["programming"])
def read_seshs_programming_month(session: SessionDep):
    cutoff_date = date.today() - timedelta(days=29)
    time = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming", Sesh.day >= cutoff_date)).one() or 0
    return {"minutes last month": time, "hours last month": time/60}


@app.get("/seshs/categorized", tags=["seshs_general"])
def read_seshs_categorized(session: SessionDep):
    types = list(SeshType)

    result = {}

    for seshtype in types:
        seshs = session.exec(select(Sesh).where(Sesh.type == seshtype)).all()
        result[seshtype.value] = seshs

    return result


@app.get("/quick_stats/", tags=["programming"])
def get_stats(session: SessionDep):
    today = date.today()
    time_total = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming")).one() or 0
    time_week = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming", Sesh.day >= today - timedelta(days=6))).one() or 0
    time_fortnight = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming", Sesh.day >= today - timedelta(days=13))).one() or 0
    time_month = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == "programming", Sesh.day >= today - timedelta(days=29))).one() or 0

    day_streak = 0
    day_skipped = False
    check_day = today

    while True:
        sesh_count = session.exec(select(func.count(Sesh.id)).where(Sesh.day == check_day, Sesh.type == "programming")).one()
        if sesh_count == 0:
            break
        else:
            check_day -= timedelta(days=1)
            day_streak += 1

    result = {
        "time_total_hours": time_total/60,
        "time_week_hours": time_week/60,
        "time_fortnight_hours": time_fortnight/60,
        "time_month_hours": time_month/60,

        "day_streak": day_streak,
    }


    return result


@app.get("/calendar-april/", tags=["calendar"])
def read_calendar_april(session: SessionDep):
    april_start = date(2026, 4, 1)
    april_end = date(2026, 4, 30)
    seshs = session.exec(select(Sesh).where(Sesh.day >= april_start, Sesh.day <= april_end, Sesh.type == "programming")).all()
    res = []
    days = [[] for i in range(0, 31)]

    for sesh in seshs:
        day_n = sesh.day.day
        days[day_n].append(sesh)

    for day_id in range(1, len(days)-1):
        day = days[day_id]
        if len(days[day_id]) > 0:
            res.append({f"April {day_id}th": day})

    return res


@app.get("/calendar/", tags=["calendar"])
def read_calendar(year: int, month: int, session: SessionDep):
    m_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    m_end = date(year, month, last_day)
    m_name = calendar.month_name[month]

    seshs = session.exec(select(Sesh).where(Sesh.day >= m_start, Sesh.day <= m_end, Sesh.type == "programming")).all()
    res = []
    days = [[] for i in range(0, 31)]

    for sesh in seshs:
        day_n = sesh.day.day
        days[day_n].append(sesh)

    for day_num in range(1, last_day+1):
        if days[day_num]:
            res.append({
                "date": f"{m_name} {day_num}th, {year}",
                "sessions": days[day_num],
                "total number of hours": sum(s.length for s in days[day_num])/60
            })

    return res









