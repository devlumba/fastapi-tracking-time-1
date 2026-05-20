from typing import Annotated
from datetime import date, timedelta
import calendar

from fastapi import FastAPI, Depends, Path, Query, Body, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, create_engine, Field, select, func
from enum import Enum
from starlette.exceptions import HTTPException

from ..dependencies import SessionDep, oauth2_scheme, UserDep
from ..models import Sesh, SeshType

router = APIRouter(prefix="/calendar", tags=["calendar"], dependencies=[Depends(oauth2_scheme)])


@router.get("/april")
def read_calendar_april(session: SessionDep, current_user: UserDep):
    april_start = date(2026, 4, 1)
    april_end = date(2026, 4, 30)
    seshs = session.exec(select(Sesh).where(
        Sesh.day >= april_start, Sesh.day <= april_end, Sesh.owner_id==current_user.id, Sesh.type == "programming")).all()
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


@router.get("/")
def read_calendar(session: SessionDep, current_user: UserDep, year: int = 2026, month: int = 4):
    m_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    m_end = date(year, month, last_day)
    m_name = calendar.month_name[month]

    seshs = session.exec(select(Sesh).where(
        Sesh.day >= m_start, Sesh.day <= m_end, Sesh.owner_id==current_user.id, Sesh.type == "programming")).all()
    res = []
    days = [[] for i in range(0, 31)]

    for sesh in seshs:
        day_n = sesh.day.day
        days[day_n].append(sesh)

    for day_num in range(1, last_day):
        print(day_num)
        print(last_day)
        if days[day_num]:
            res.append({
                "date": f"{m_name} {day_num}th, {year}",
                "sessions": days[day_num],
                "total number of hours": sum(s.length for s in days[day_num])/60
            })

    return res


def month_to_num(shortMonth):
    return {
            'jan': 1,
            'feb': 2,
            'mar': 3,
            'apr': 4,
            'may': 5,
            'jun': 6,
            'jul': 7,
            'aug': 8,
            'sep': 9,
            'oct': 10,
            'nov': 11,
            'dec': 12
    }[shortMonth]


@router.get("/{year}/{month_name}")
async def read_specific_month(session: SessionDep, current_user: UserDep,
        year: Annotated[int, Path(le=2030, ge=2026)],
        month_name: Annotated[str, Path(min_length=3, max_length=3)]):

    month = month_to_num(month_name)
    m_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    m_end = date(year, month, last_day)
    m_name = calendar.month_name[month]
    seshs = session.exec(select(Sesh).where(
        Sesh.day >= m_start, Sesh.day <= m_end, Sesh.owner_id==current_user.id, Sesh.type == "programming")).all()

    res = []
    m_name = calendar.month_name[month]

    for sesh in seshs:
        day_n = sesh.day.day
        res.append(sesh)


    return {f"Seshs from {m_name} {year}:": res}


@router.get("/{year}/{month}/{day}", summary="Read Specific Day")
async def read_specific_day(session: SessionDep, current_user: UserDep,
        year: Annotated[int, Path(le=2030, ge=2026)],
        month: Annotated[int, Path(le=12, ge=1)],
        day: Annotated[int, Path(le=31, ge=1)]):
    seshs = session.exec(select(Sesh).where(
        Sesh.day == date(year, month, day), Sesh.owner_id==current_user.id, Sesh.type == "programming")).all()
    res = []
    m_name = calendar.month_name[month]

    for sesh in seshs:
        day_n = sesh.day.day
        res.append(sesh)


    return {f"Seshs on {m_name} {day}th, {year}:": res}


@router.get("/by_sesh/{year}/{month}/{sesh_type}")  # i wonder about the order though
async def read_calendar_sesh_type(session: SessionDep, current_user: UserDep,
                                  sesh_type: Annotated[SeshType, Path()], year: Annotated[int, Path()],
                                  month: Annotated[int, Path()]):
    m_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    m_end = date(year, month, last_day)
    seshs = session.exec(select(Sesh).where(
        Sesh.day >= m_start, Sesh.day <= m_end, Sesh.owner_id==current_user.id, Sesh.type == sesh_type)).all()

    res = []

    for sesh in seshs:
        day_n = sesh.day.day
        res.append(sesh)


    return {f"Seshs from {month} {year}:": res}

