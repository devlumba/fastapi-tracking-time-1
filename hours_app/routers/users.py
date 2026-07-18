from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import FastAPI, Depends, APIRouter, Query, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pwdlib import PasswordHash
from jwt.exceptions import InvalidTokenError
from sqlmodel import select

from hours_app.dependencies import (SessionDep, oauth2_scheme, HTMXContext, get_htmx_context, get_user,
                                    get_current_user, ALGORITHM, SECRET_KEY, get_template_context)
from hours_app.models import Sesh, UserInDB, Token, TokenData, UserBase, UserCreate, UserPublic
from hours_app.database import Session
from hours_app.templates import templates
from hours_app.config import settings



ACCESS_TOKEN_EXPIRE_MINUTES = 6000

password_hash = PasswordHash.recommended()  # I assume this is me choosing HOW to hash/unhash a password

DUMMY_HASH = password_hash.hash("dummypassword")



router = APIRouter(tags=["users"])


def verify_password(plain_password, hashed_password) -> str:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(plain_password) -> str:
    return password_hash.hash(plain_password)


def authenticate_user(session: SessionDep, username: str, password: str):
    user = get_user(session=session, username=username)
    if not user:
        verify_password(password, DUMMY_HASH)  # so you can't bruteforce guess which usernames exist
        return False
    pass_verified = verify_password(password, user.hashed_password)  # for clarity
    if not pass_verified:
        return False

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str: # encode returns a string, apparently
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/token")
async def login_for_access_token(session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:  # depends on the type/class itself, i could put OAuth...Form in the parentheses of Depends
    user = authenticate_user(session, username=form_data.username, password=form_data.password)
    if not user:  # this probably could be more explicit and understandable
        raise HTTPException(status_code=401, detail="Incorrect Username or Password",
                            headers={"WWW-Authenticate": "Bearer"})  # once again I gotta use headers for 401
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")



@router.post("/users/")
async def create_user(ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
                      username: Annotated[str, Form()],
                      password: Annotated[str, Form()],
                      confirm_password: Annotated[str, Form()],
                      full_name: Annotated[str, Form()] | None = None):
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

    htmx_header = ctx.request.headers.get("HX-Request") == "true"
    if not htmx_header:
        return UserPublic.model_validate(db_user)

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


@router.put("/users/")
def update_user(user_id: int, username: Annotated[str, Form()], ctx: Annotated[HTMXContext, Depends(get_htmx_context)],
                full_name: Annotated[str | None, Form()] = None):
    user = ctx.session.get(UserInDB, user_id)

    if not ctx.current_user:
        raise HTTPException(status_code=401)
    if not user:
        raise HTTPException(status_code=404, detail="no such user")
    if user.id != ctx.current_user.id:
        raise HTTPException(status_code=403, detail="not u")

    user.sqlmodel_update({"username": username, "full_name": full_name})
    print("1233333333")
    print("1233333333")
    print("1233333333")
    print("1233333333")
    print(user)
    print(type(user))
    ctx.session.add(user)
    ctx.session.commit()
    ctx.session.refresh(user)
    return user


@router.delete("/users/")
def delete_user(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], user_id: int):
    user = ctx.session.get(UserInDB, user_id)
    if not ctx.current_user:  # not sure i need this?
        raise HTTPException(status_code=401)
    if not user:
        raise HTTPException(status_code=404, detail="no such user")
    if user.id != ctx.current_user.id:
        raise HTTPException(status_code=403, detail="not u")

    ctx.session.delete(user)
    return "user deleted"


@router.get("/users/")
async def read_users_all(session: SessionDep) -> list[UserPublic]:
    users = session.exec(select(UserInDB)).all()
    return users

#
# @router.get("/users/{username:str}")
# async def read_specific_user(session: SessionDep, username: str) -> UserPublic:
#     user = session.exec(select(UserInDB).where(UserInDB.username==username)).first()
#     if not user:
#         raise HTTPException(status_code=404, detail='fot nound')
#     return user
#

@router.get("/users/me")
async def read_own_profile(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if not ctx.current_user:
        raise HTTPException(status_code=401)
    return ctx.current_user


@router.get("/users/me/seshs")
async def read_own_seshs(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if not ctx.current_user:
        raise HTTPException(status_code=401)
    seshs = ctx.session.exec(select(Sesh).where(Sesh.owner_id==ctx.current_user.id)).all()
    return seshs


@router.get("/logout")
async def logout(ctx: Annotated[HTMXContext, Depends(get_htmx_context)]):
    if not ctx.current_user:
        raise HTTPException(status_code=401)
    pass


@router.get("/allseshs")
def read_all_seshs(session: SessionDep):
    seshs = session.exec(select(Sesh)).all()
    return seshs


