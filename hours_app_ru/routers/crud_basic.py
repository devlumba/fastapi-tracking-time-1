from datetime import date, timedelta
from typing import Annotated

from fastapi import FastAPI, Depends, Path, Query, Body, APIRouter
from sqlmodel import Session, SQLModel, create_engine, Field, select, func
from starlette.exceptions import HTTPException

from hours_app.dependencies import SessionDep, oauth2_scheme
from hours_app.models import Sesh, SeshType, SeshCreate, SeshBase, SeshUpdate, UserInDB
from hours_app.routers.users import get_current_user


router = APIRouter(tags=["crud(создание-просмотр-обновление-удаление)"],
                   dependencies=[Depends(oauth2_scheme)], prefix="/seshs")


@router.get("/", summary="Просмотр записей о занятиях", dependencies=[Depends(oauth2_scheme)])
def read_seshs(session: SessionDep, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    seshs = session.exec(select(Sesh).where(Sesh.owner_id == current_user.id)).all()
    return seshs


@router.post("/", summary="Создание записей о занятиях")
def create_seshs(session: SessionDep, current_user: Annotated[UserInDB, Depends(get_current_user)],
                 sesh_length: int, sub_tag_one: str = None, sub_tag_two: str = None,
                 sesh_desc: str = None,  # i COULD add annotation with restrictions here # todoooooooooooooooo
                 sesh_type: SeshType = "programming",
                 sesh_day: date = date.today(),):
    db_sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=current_user.id,
                   sub_tag_one=sub_tag_one, sub_tag_two=sub_tag_two)
    # db_sesh = Sesh.model_validate(sesh)
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


@router.delete("/", summary="Удаление записей по id")
def delete_seshs(session: SessionDep, sesh_id: int, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    sesh = session.get(Sesh, sesh_id)
    if not sesh:
        print("FUCKING KILL YOUSEFL")
        raise HTTPException(status_code=404, detail="Ошибка 404")
    if sesh.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Не ваша запись")

    session.delete(sesh)
    session.commit()
    return {"msg": "Успешно Удалено"}


@router.put("/", summary="Изменение записей по id")
def update_sesh(session: SessionDep, sesh: SeshUpdate,
                sesh_id: int, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    db_sesh = session.get(Sesh, sesh_id)
    if not db_sesh:
        raise HTTPException(status_code=404, detail="Ошибка 404")
    if db_sesh.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Не ваша запись")

    sesh_data = sesh.model_dump(exclude_unset=True)
    db_sesh.sqlmodel_update(sesh_data)
    session.add(db_sesh)
    session.commit()
    session.refresh(db_sesh)
    return db_sesh


