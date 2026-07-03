from datetime import date, timedelta
from typing import Annotated

from fastapi import FastAPI, Depends, Path, Query, Body, APIRouter, Form
from sqlmodel import Session, SQLModel, create_engine, Field, select, func, desc
from starlette.exceptions import HTTPException

from hours_app.dependencies import SessionDep, oauth2_scheme, get_template_context, HTMXContext, get_htmx_context, get_current_user_or_none
from hours_app.models import Sesh, SeshType, SeshCreate, SeshBase, SeshUpdate, UserInDB
from hours_app.routers.users import get_current_user
from hours_app.templates import templates


router = APIRouter(tags=["crud"], prefix="/seshs")


@router.get("/", summary="Read Seshs, clearly your own", dependencies=[Depends(oauth2_scheme)])
def read_seshs(session: SessionDep, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    htmx_header = ctx.request.headers.get("HX-Request") == "true"
    seshs = ctx.session.exec(select(Sesh).where(Sesh.owner_id==ctx.current_user.id).order_by(Sesh.day.desc())).all()
    if htmx_header:
        context = get_template_context(ctx, {"seshs": seshs})
        return templates.TemplateResponse(request=ctx.request, name="list_seshs.html", context=context)
    return seshs



@router.post("/")
def create_seshs(ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
                 sesh_length: Annotated[int, Form()],
                 sesh_desc: Annotated[str | None, Form()] = None,  # i COULD add annotation with restrictions here # todoooooooooooooooo
                 sesh_type: Annotated[str, Form()] = "programming",
                 sesh_day: Annotated[date, Form()] = date.today()):
    htmx_header = ctx.request.headers.get("HX-Request") == "true"

    if htmx_header:
        if not ctx.current_user:
            return templates.TemplateResponse(
                request=ctx.request, name="login_form.html",
                context={"message": "You must be logged in in order to create a sesh"})
        sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=ctx.current_user.id)
        ctx.session.add(sesh)
        ctx.session.commit()
        ctx.session.refresh(sesh)
        return templates.TemplateResponse(
            request=ctx.request, name="specific_sesh.html", context={"sesh": sesh, "current_user": ctx.current_user})

    print(ctx.current_user)
    if not htmx_header:
        if not ctx.current_user:
            raise HTTPException(status_code=401)
        sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=ctx.current_user.id)
        print(sesh)
        ctx.session.add(sesh)
        ctx.session.commit()
        ctx.session.refresh(sesh)

    return sesh


@router.delete("/", response_model=None)
def delete_seshs(sesh_id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    sesh = ctx.session.get(Sesh, sesh_id)
    if not sesh:
        print("FUCKING KILL YOUSEFL")
        raise HTTPException(status_code=404, detail="FUCKING KILL YOURSELF")
    if sesh.owner_id != ctx.current_user.id:
        raise HTTPException(status_code=403, detail="Not Your Sesh")

    ctx.session.delete(sesh)
    ctx.session.commit()

    htmx_header = ctx.request.headers.get("HX-Request") == "true"
    if not htmx_header:
        return {"msg": "fuck off aye"}
    return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "Deleted successfully"})


@router.put("/{sesh_id}")
def update_sesh(
                sesh_id: int,
                ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
                sesh_length: Annotated[int, Form()],
                sesh_desc: Annotated[str | None, Form()] = None,  # i COULD add annotation with restrictions here # todoooooooooooooooo
                sesh_type: Annotated[str, Form()] = "programming",
                sesh_day: Annotated[date, Form()] = date.today()):
    sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=ctx.current_user.id)
    db_sesh = ctx.session.get(Sesh, sesh_id)
    if not db_sesh:
        raise HTTPException(status_code=404, detail="nope mate")
    if db_sesh.owner_id != ctx.current_user.id:
        raise HTTPException(status_code=403, detail="Not Your Sesh")

    sesh_data = sesh.model_dump(exclude_unset=True)
    db_sesh.sqlmodel_update(sesh_data)
    ctx.session.add(db_sesh)
    ctx.session.commit()
    ctx.session.refresh(db_sesh)
    return db_sesh


@router.get("/{sesh_id}")
def read_specific_sesh(session: SessionDep,
                sesh_id: int, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    sesh = session.get(Sesh, sesh_id)
    if not sesh:
        raise HTTPException(status_code=404, detail="nope mate")
    if sesh.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not Your Sesh")

    return sesh

