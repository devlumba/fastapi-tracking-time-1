import datetime
from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, and_, or_
from pydantic import BaseModel

from hours_app.models import Sesh, UserInDB, UserCreate, UserPublic, Token, SeshCreate
from hours_app.dependencies import SessionDep
from hours_app.routers.users import (get_password_hash, SECRET_KEY, get_user,
                                     ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, authenticate_user)
from hours_app.security import get_current_user_or_none, token_decode
from hours_app.config import settings


router = APIRouter(tags=["interactions(HTMX SPA)"])

from hours_app.templates import templates


class HTMXContext(BaseModel):
    request: Request
    session: SessionDep
    current_user: UserInDB | None = None

    class Config:
        arbitrary_types_allowed = True


async def get_htmx_context(request: Request, session: SessionDep,
                           current_user: Annotated[(UserInDB, Depends(get_current_user_or_none))]):
    ctx = HTMXContext(request=request, session=session, current_user=current_user)
    return ctx


def get_access_token(request: Request, session: SessionDep, *args):  # == get user from token
    token = request.cookies.get("access_token")
    if not token:
        return None
    user_username = token_decode(token)
    current_user_db = get_user(session, user_username)

    # if not current_user_db:
    #     context = {"request": request}
    #     context["current_user"] = None
    #     return context

    current_user = UserPublic.model_validate(current_user_db)
    context = {"request": request}  # not really
    # needed cause you still gotta pass a separate request when calling TemplateResponse

    if current_user:
        context["current_user"] = current_user

    context.update(*args)
    return context


def get_template_context(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], *args):
    context = {}

    if ctx.current_user:
        context["current_user"] = ctx.current_user

    context.update(*args)
    return context


@router.get("/interactions")
async def base_interacting_endpoint(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    context = get_template_context(ctx)
    return templates.TemplateResponse(request=ctx.request, name="base.html", context=context)


@router.get("/seshs/all", summary="htmx read YOUR seshs")
async def read_all_seshs(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    seshs = ctx.session.exec(select(Sesh).where(Sesh.owner_id==ctx.current_user.id).order_by(Sesh.day.desc())).all()
    context = get_template_context(ctx, {"seshs": seshs})
    return templates.TemplateResponse(request=ctx.request, name="list_seshs.html", context=context)


@router.get("/register-form")
async def pull_up_a_register_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="specific_user.html",
                                          context={"user": ctx.current_user, "current_user": ctx.current_user})
    return templates.TemplateResponse(request=ctx.request,
                                      name="register_form.html", context={"current_user": ctx.current_user})


@router.post("/register")  # not async cause db session
def create_user_from_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], username: Annotated[str, Form()],
        password: Annotated[str, Form()],  confirm_password: Annotated[str, Form()],
        full_name: Annotated[str | None, Form()] = None):

    user = UserCreate(username=username, password=password, full_name=full_name)
    if confirm_password != password:
        raise HTTPException(status_code=401, detail="Passwords Not Matching")
    supposed_user = ctx.session.exec(select(UserInDB).where(UserInDB.username == username)).first()
    if supposed_user:
        raise HTTPException(status_code=400, detail="This Username is Already Taken")

    hashed_password = get_password_hash(user.password)
    db_user_preval = UserInDB(username=user.username, full_name=user.full_name, hashed_password=hashed_password)
    db_user = UserInDB.model_validate(db_user_preval)
    ctx.session.add(db_user)
    ctx.session.commit()
    ctx.session.refresh(db_user)
    user_public = UserPublic.model_validate(db_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_public.username}, expires_delta=access_token_expires
    )
    context = get_template_context(ctx, {"user": user_public, "current_user": user_public})
    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="specific_user.html",
        context=context
    )
    template_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain=settings.COOKIE_DOMAIN,
        max_age=60 * 60 * 24 * 7,
        path = "/"
    )

    return template_response


@router.get("/login-form")
async def pull_up_a_login_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="specific_user.html",
                                          context={"user": ctx.current_user, "current_user": ctx.current_user, "message": "nuh uh"})
    return templates.TemplateResponse(request=ctx.request, name="login_form.html")


@router.post("/login")
async def login_htmx(
        ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:  # depends on the type/class itself, i could put OAuth...Form in the parentheses of Depends

    # print("logged in", form_data.username, form_data.password)
    user = authenticate_user(ctx.session, username=form_data.username, password=form_data.password)
    if not user:  # this probably could be more explicit and understandable
        raise HTTPException(status_code=401, detail="Incorrect Username or Password",
                            headers={"WWW-Authenticate": "Bearer"})  # once again I gotta use headers for 401
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    ready_token = Token(access_token=access_token, token_type="bearer")  # for potential headers
    # print(user)
    context = get_template_context(ctx, {"user": user, "current_user": user})
    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="specific_user.html",
        context=context
    )
    template_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain=settings.COOKIE_DOMAIN,
        max_age=60 * 60 * 24 * 7,
        path = "/"
    )

    # template_response.headers["Authorization": f"Bearer {access_token}"]
    return template_response


@router.get("/users-all")
def read_users_all(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    users = ctx.session.exec(select(UserInDB)).all()
    users_public = [UserPublic.model_validate(u) for u in users]
    return templates.TemplateResponse(ctx.request,
                                      name="list_users.html",
                                      context={"users": users_public, "current_user": ctx.current_user})


@router.get("/specific-user/{id:int}")  # 2 issues: 1) overlaps with /users/str, 2) could be higher than register
    # yeah i gotta merge htmx and swagger endpoints with if request.header hx and stuff, check notes for 2026-06-01
def read_specific_user(id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    user = ctx.session.get(UserInDB, id)
    user_public = UserPublic.model_validate(user)
    return templates.TemplateResponse(ctx.request, name="specific_user.html", context={"user": user_public, "current_user": ctx.current_user})


@router.get("/get-curr-user")
def read_curr_user_htmx(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    user = get_current_user_or_none(ctx.session, ctx.request)
    # print(user)
    return templates.TemplateResponse(ctx.request, name="specific_user.html", context={"user": user, "current_user": ctx.current_user})


@router.get("/logout")
async def logout(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):

    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="loggedout.html"
    )
    template_response.set_cookie(
        key="access_token",
        value="",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain=settings.COOKIE_DOMAIN,
        max_age=0,
        path = "/"
    )

    return template_response


@router.post("/search_results")
def get_post_search_results(q: Annotated[str, Form()], ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if q.isdigit():
        result = ctx.session.exec(select(Sesh).where(Sesh.length == int(q), Sesh.owner_id==ctx.current_user.id)).all()
        result += ctx.session.exec(select(Sesh).where(Sesh.specifics.contains(q), Sesh.owner_id==ctx.current_user.id))
        context = get_template_context(ctx, {"objects": result})
        if not result:
            context = get_template_context(ctx, {"message": "Nothing has been found"})
            return templates.TemplateResponse(ctx.request, name="return_message.html", context=context)
        return templates.TemplateResponse(ctx.request, name="search_results.html", context=context)

    result = ctx.session.exec(select(Sesh).where(Sesh.specifics.contains(q), Sesh.owner_id==ctx.current_user.id)).all()
    context = get_template_context(ctx, {"objects": result})
    if not result:
        context = get_template_context(ctx, {"message": "Nothing has been found"})
        return templates.TemplateResponse(ctx.request, name="return_message.html", context=context)
    return templates.TemplateResponse(ctx.request, name="search_results.html", context=context)


@router.get("/sesh-create-form")
async def create_sesh_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if not ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="login-form.html",
                                          context={"message": "You gotta log into your account first"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="sesh_form.html", context={"current_user": ctx.current_user})


@router.post("/sesh-create")  # not async cause db session
def create_sesh_from_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], sesh_length: Annotated[int, Form()],
        sesh_desc: Annotated[str | None, Form()] = None,  sesh_type: Annotated[str, Form()] = "programming",
        sesh_day: Annotated[datetime.date, Form()] = datetime.date.today):
    if not ctx.current_user:
        return templates.TemplateResponse(
            request=ctx.request, name="login_form.html",
            context={"message": "You must be logged in in order to create a sesh"})
    sesh = Sesh(length=sesh_length, specifics=sesh_desc, day=sesh_day, type=sesh_type, owner_id=ctx.current_user.id)
    print(sesh)

    ctx.session.add(sesh)
    ctx.session.commit()
    ctx.session.refresh(sesh)
    return templates.TemplateResponse(
        request=ctx.request, name="specific_sesh.html", context={"sesh": sesh, "current_user": ctx.current_user})


@router.delete("/sesh-delete/{id}")
def delete_sesh_htmx(id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    sesh = ctx.session.get(Sesh, id)
    if sesh.owner_id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "ur not the owner of the post"})
    ctx.session.delete(sesh)
    ctx.session.commit()
    return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "Deleted successfully"})


@router.get("/sesh-update-form/{id}")
async def update_sesh_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], id: int):
    sesh = ctx.session.get(Sesh, id)
    if sesh.owner_id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "ur not the owner of the post"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="sesh_update_form.html", context={"current_user": ctx.current_user, "sesh": sesh})


@router.post("/sesh-update/{id}")  # not async cause db session
def update_sesh_from_form(id: int,
        ctx: Annotated[HTMXContext, Depends(get_htmx_context)], sesh_length: Annotated[int, Form()],
        sesh_desc: Annotated[str | None, Form()] = None,  sesh_type: Annotated[str, Form()] = "programming",
        sesh_day: Annotated[datetime.date, Form()] = datetime.date.today):
    sesh = ctx.session.get(Sesh, id)
    sesh.sqlmodel_update({"length": sesh_length, "specifics": sesh_desc, "day": sesh_day, "type":sesh_type})
    ctx.session.add(sesh)
    ctx.session.commit()
    ctx.session.refresh(sesh)
    return templates.TemplateResponse(
        request=ctx.request, name="specific_sesh.html", context={"sesh": sesh, "current_user": ctx.current_user})


@router.delete("/user-delete/{id}")
def delete_user_htmx(id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    user = ctx.session.get(UserInDB, id)
    if user.id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                                  "message": "ur not the owner of the account"})
    ctx.session.delete(user)
    ctx.session.commit()


    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="return_message.html",
        context={"message": "Account Deleted Successfully"}
    )
    template_response.set_cookie(
        key="access_token",
        value="",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain=settings.COOKIE_DOMAIN,
        max_age=0,
        path = "/"
    )

    return template_response


@router.get("/user-update-form/{id}")
async def update_user_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], id: int):
    user = ctx.session.get(UserInDB, id)
    if user.id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "ur not the owner of the account"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="user_update_form.html", context={"current_user": ctx.current_user, "user": user})


@router.post("/user-update/{id}")  # not async cause db session
def update_user_from_form(id: int,
        ctx: Annotated[HTMXContext, Depends(get_htmx_context)], username: Annotated[str, Form()],
        full_name: Annotated[str | None, Form()] = None):
    print(username, full_name)
    user = ctx.session.get(UserInDB, id)
    user.sqlmodel_update({"username": username, "full_name": full_name})
    ctx.session.add(user)
    ctx.session.commit()
    ctx.session.refresh(user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    context = get_template_context(ctx, {"user": user, "current_user": user})
    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="specific_user.html",
        context=context
    )
    template_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain=settings.COOKIE_DOMAIN,
        max_age=60 * 60 * 24 * 7,
        path = "/"
    )

    return template_response


@router.get("/specific-sesh/{id}")
def read_specific_post(id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    sesh = ctx.session.get(Sesh, id)
    context = get_template_context(ctx, {"sesh": sesh})
    return templates.TemplateResponse(ctx.request, name="specific_sesh.html", context=context)


