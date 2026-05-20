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
from ..models import Sesh, SeshBase, SeshCreate, SeshUpdate, SeshType, UserInDB
from .users import get_current_user

router = APIRouter(prefix="/seshs", tags=["crud-detailed"], dependencies=[Depends(oauth2_scheme)])


@router.get("/{sesh_type}/all", summary="Read All Seshs of a Certain sesh_type")
async def read_seshs_by_type(session: SessionDep,
                             current_user: Annotated[UserInDB, Depends(get_current_user)],
                             sesh_type: SeshType = "programming"):
    seshs = session.exec(select(Sesh).where(Sesh.type==sesh_type, Sesh.owner_id==current_user.id)).all()
    return {f"All seshs from {type}:": seshs}


@router.get("/{sesh_type}/time/", summary="Read Just Time of a Certain sesh_type(total of all time)")
def read_time_age(sesh_type: SeshType, age: int, session: SessionDep, current_user: UserDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= cutoff_day)).all()
    sum = 0
    for i in seshs:
        sum += i.length
    return {"minutes": sum, "hours": sum/60}


@router.get("/{sesh_type}/time/week",
         summary="Get Total Time Spent on a Certain sesh_type Last Week")
def read_seshs_type_week(session: SessionDep, current_user: UserDep, sesh_type: SeshType = "programming"):
    cutoff_date = date.today() - timedelta(days=6)
    time = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= cutoff_date)).one() or 0
    return {f"Reading minutes/hours of past week for {sesh_type.name}: ":
                {"minutes last week": time, "hours last week": time / 60}}


@router.get("/{sesh_type}/quick_stats",
         summary="Get total_hours and day_streak for a certain sesh_type from a certain date to today")
def get_full_stats_type_age(session: SessionDep, current_user: UserDep, sesh_type: SeshType = "programming", cutoff_date: date = date.today()):
    today = date.today()
    time_total = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= cutoff_date, Sesh.day <= today)).one() or 0

    day_streak = 0
    day_skipped = False
    check_day = today

    while True:
        sesh_count = session.exec(select(func.count(Sesh.id)).where(Sesh.day == check_day, Sesh.type == sesh_type)).one()
        if sesh_count == 0:
            break
        else:
            check_day -= timedelta(days=1)
            day_streak += 1

    result = {
        "time_total_hours": time_total/60,

        "day_streak": day_streak,
    }

    return {f"Quick stats for {sesh_type} since {cutoff_date}:": result}


@router.get("/{sesh_type}/full_stats",
         summary="Get Stats for a selected sesh_type(total hours, "
                 "time last week, fortnight, month, and a day streak)")
def get_stats_type(session: SessionDep, current_user: UserDep, sesh_type: SeshType = "programming"):
    today = date.today()
    time_total = session.exec(select(func.sum(Sesh.length)).where(
        Sesh.type == sesh_type, Sesh.owner_id==current_user.id)).one() or 0
    time_week = session.exec(select(func.sum(Sesh.length)).where(
        Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= today - timedelta(days=6))).one() or 0
    time_fortnight = session.exec(select(func.sum(Sesh.length)).where(
        Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= today - timedelta(days=13))).one() or 0
    time_month = session.exec(select(func.sum(Sesh.length)).where(
        Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= today - timedelta(days=29))).one() or 0

    day_streak = 0
    day_skipped = False
    check_day = today

    while True:
        sesh_count = session.exec(select(func.count(Sesh.id)).where(
            Sesh.day == check_day, Sesh.owner_id==current_user.id, Sesh.type == sesh_type, Sesh.owner_id==current_user.id)).one()
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

    return {f"Quick stats for {sesh_type.name}:": result}



