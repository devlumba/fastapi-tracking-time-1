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

from hours_app.dependencies import SessionDep, oauth2_scheme, UserDep
from hours_app.models import Sesh, SeshBase, SeshCreate, SeshUpdate, SeshType, UserInDB
from hours_app.routers.users import get_current_user

router = APIRouter(prefix="/seshs", tags=["crud-детализированный"], dependencies=[Depends(oauth2_scheme)])


@router.get("/{sesh_type}/all", summary="Просмотреть все записи определенного типа")
async def read_seshs_by_type(session: SessionDep,
                             current_user: Annotated[UserInDB, Depends(get_current_user)],
                             sesh_type: SeshType = "programming"):
    seshs = session.exec(select(Sesh).where(Sesh.type==sesh_type, Sesh.owner_id==current_user.id)).all()
    return {f"Все записи типа '{sesh_type}':": seshs}


@router.get("/{sesh_type}/time/", summary="Посмотреть сумму времени записей определенного типа")
def read_time_age(sesh_type: SeshType, age: int, session: SessionDep, current_user: UserDep):
    cutoff_day = date.today() - timedelta(days=age)
    seshs = session.exec(select(Sesh).where(Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= cutoff_day)).all()
    sum = 0
    for i in seshs:
        sum += i.length
    return {"минут": sum, "часов": sum/60}


@router.get("/{sesh_type}/time/week",
         summary="Просмотреть, сколько времени было проведено над определенным типом записи за последнюю неделю")
def read_seshs_type_week(session: SessionDep, current_user: UserDep, sesh_type: SeshType = "programming"):
    cutoff_date = date.today() - timedelta(days=6)
    time = session.exec(select(func.sum(Sesh.length)).where(Sesh.type == sesh_type, Sesh.owner_id==current_user.id, Sesh.day >= cutoff_date)).one() or 0
    return {f"Просмотр минут/часов за последнюю неделю у типа '{sesh_type.name}': ":
                {"минут": time, "часов": time / 60}}


@router.get("/{sesh_type}/quick_stats",
         summary="Просмотреть суммарное кол-во часов и сколько дней подряд выполяется определенный тип записи. От определенного дня по сегодня")
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
        "Часов Проведено Всего": time_total/60,

        "Дней подряд": day_streak,
    }

    return {f"Сокращенная статистика для типа '{sesh_type}' начиная с {cutoff_date}:": result}


@router.get("/{sesh_type}/full_stats",
         summary="Получить статистику по определнному типу записей(тотал часов,"
                 "время за последнюю неделю, 2 недели, месяц, и сколько дней подряд.")
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
        "Часов Проведено Всего": time_total/60,
        "Часов Проведено за Последнюю Неделю": time_week/60,
        "Часов Проведено За Последние 2 Недели": time_fortnight/60,
        "Часов Проведено За Последний Месяц": time_month/60,

        "Дней подряд": day_streak,
    }

    return {f"Сокращенная статистика для типа '{sesh_type.name}':": result}



