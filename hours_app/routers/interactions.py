from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, and_, or_
from pydantic import BaseModel

from hours_app.models import Sesh, UserInDB, UserCreate, UserPublic, Token
from hours_app.dependencies import SessionDep
from hours_app.routers.users import (get_password_hash, SECRET_KEY, get_user,
                                     ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, authenticate_user)
from hours_app.security import get_current_user_or_none, token_decode


router = APIRouter(tags=["interactions"])

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


@router.get("/seshs/all", summary="endpoint for htmx. I kinda should add a similar one to swagger? nah")
async def read_all_seshs(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    seshs = ctx.session.exec(select(Sesh)).all()
    context = get_template_context(ctx, {"seshs": seshs})
    return templates.TemplateResponse(request=ctx.request, name="return.html", context=context)


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
    return templates.TemplateResponse(request=ctx.request, name="specific_user.html", context={"user": user_public})  # no idea how to tweak this one. Redirect likely won't do with htmx


@router.get("/login-form")
async def pull_up_a_login_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="specific_user.html",
                                          context={"user": ctx.current_user, "current_user": ctx.current_user})
    return templates.TemplateResponse(request=ctx.request, name="login_form.html")


@router.post("/login")
async def login_htmx(
        ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:  # depends on the type/class itself, i could put OAuth...Form in the parentheses of Depends

    print("logged in", form_data.username, form_data.password)
    user = authenticate_user(ctx.session, username=form_data.username, password=form_data.password)
    if not user:  # this probably could be more explicit and understandable
        raise HTTPException(status_code=401, detail="Incorrect Username or Password",
                            headers={"WWW-Authenticate": "Bearer"})  # once again I gotta use headers for 401
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    ready_token = Token(access_token=access_token, token_type="bearer")  # for potential headers
    print(user)
    context = get_template_context(ctx, {"user": user, "current_user": user})
    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="specific_user.html",
        context=context
    )
    template_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,
        secure=False,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain="localhost",
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


@router.get("/specific_user/{id:int}")  # 2 issues: 1) overlaps with /users/str, 2) could be higher than register
    # yeah i gotta merge htmx and swagger endpoints with if request.header hx and stuff, check notes for 2026-06-01
def read_specific_user(id: int, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    user = ctx.session.get(UserInDB, id)
    user_public = UserPublic.model_validate(user)
    return templates.TemplateResponse(ctx.request, name="specific_user.html", context={"user": user_public, "current_user": ctx.current_user})


@router.get("/get-curr-user")
def read_curr_user_htmx(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    user = get_current_user_or_none(ctx.session, ctx.request)
    print(user)
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
        httponly=False,
        secure=False,  # should set to True in production(HTTPS)
        samesite="lax",  # CORS stuff, lax allows between site cookie sending
        domain="localhost",
        max_age=0,
        path="/"
    )

    return template_response


@router.post("/search_results")
def get_post_search_results(input: str, ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if input.isdigit():
        result = ctx.session.exec(select(Sesh).where(or_(Sesh.length == int(str)), or_(Sesh.specifics.contains(input)))).all()
        context = get_template_context(ctx, {"objects": result})
        return templates.TemplateResponse(ctx.request, name="search_result.html", context=context)

    result = ctx.session.exec(select(Sesh).where(Sesh.specifics.contains(input))).all()
    context = get_template_context(ctx, {"objects": result})
    return templates.TemplateResponse(ctx.request, name="search_result.html", context=context)

