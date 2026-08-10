import datetime
from typing import Annotated
from datetime import timedelta

from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, and_, or_
from pydantic import BaseModel

from hours_app.models import Sesh, UserInDB, UserCreate, UserPublic, Token, SeshCreate
from hours_app.dependencies import SessionDep, get_template_context, get_htmx_context, HTMXContext, \
    get_current_user_or_none, oauth2_scheme
from hours_app.routers.users import (get_password_hash, SECRET_KEY, get_user,
                                     ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, authenticate_user)
from hours_app.security import token_decode
from hours_app.config import settings


router = APIRouter(tags=["interactions(HTMX SPA)"])

from hours_app.templates import templates


@router.get("/interactions")
async def base_interacting_endpoint(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    context = get_template_context(ctx=ctx)
    return templates.TemplateResponse(request=ctx.request, name="base.html", context=context)


@router.get("/register-form")
async def get_register_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="specific_user.html",
                                          context={"user": ctx.current_user, "current_user": ctx.current_user})
    return templates.TemplateResponse(request=ctx.request,
                                      name="register_form.html", context={"current_user": ctx.current_user})


@router.get("/login-form")
async def get_login_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
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
    context = get_template_context(ctx, {"user": user, "current_user": user, "token": access_token})
    template_response = templates.TemplateResponse(
        request=ctx.request,
        name="specific_user.html",
        context=context,
        headers={"Authorization": f"Bearer {access_token}"}
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
    today_day = datetime.date.today()
    if not ctx.current_user:
        return templates.TemplateResponse(ctx.request,
                                          name="login-form.html",
                                          context={"message": "You gotta log into your account first"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="sesh_form.html", context={"current_user": ctx.current_user, "today_day": today_day})


@router.get("/sesh-update-form/{id}")
async def update_sesh_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], id: int):
    sesh = ctx.session.get(Sesh, id)
    if sesh.owner_id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                      "message": "ur not the owner of the post"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="sesh_update_form.html",
                                      context={"current_user": ctx.current_user, "sesh": sesh})


@router.get("/user-update-form/{id}")
async def update_user_form(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], id: int):
    user = ctx.session.get(UserInDB, id)
    if user.id != ctx.current_user.id:
        return templates.TemplateResponse(ctx.request, name="base.html", context={"current_user": ctx.current_user,
                                                                              "message": "ur not the owner of the account"})
    return templates.TemplateResponse(request=ctx.request,
                                      name="user_update_form.html", context={"current_user": ctx.current_user, "user": user})

