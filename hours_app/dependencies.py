from typing import Annotated
from dataclasses import dataclass

from sqlmodel import Session
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, Field, ConfigDict
from sqlmodel import select

from hours_app.database import get_session
from hours_app.models import UserInDB, TokenData


SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "f9208ed4f21b01559b9445e324694d6b7b0d48ab4bdece5364ce9cafbbb49079"
ALGORITHM = "HS256"


async def get_current_user(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=401, detail="invalid credentials", headers={"WWW-Authenticate": "Bearer"} # need headers
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # several algorithms ohhhh
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:  # so you give a credentials exception, not 501 server dead
        raise credentials_exception
    user = get_user(session, username=token_data.username)  # or just username = username?
    if user is None:
        raise credentials_exception
    return user


def get_user(session: Session, username: str) -> UserInDB:
    # print("SESSSSSSIon", session)
    user = session.exec(select(UserInDB).where(UserInDB.username == username)).first()
    if user:
        return user
    else:
        print("AHHHHHHHHHHHHHHH NOOOOOOOOOOOO USERRRR OH NOOOOOOOOOOOOOOOOOOOO 500 500 500 500 500 500 500 500")




UserDep = Annotated[UserInDB, Depends(get_current_user)]


def get_current_user_or_none(session: SessionDep, request: Request) -> UserInDB:
    token = request.cookies.get("access_token")
    header_token = request.headers.get("Authorization")
    if header_token:
        header_token = header_token[7:]
    user_true = False
    print("cookie token is", token)
    print("header token is ", header_token)
    if not token and not header_token:
        print("no bueno")
        return None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            user = get_user(session, username)
            if not user:
                print("no user")
            else:
                user_true = True
        except InvalidTokenError:
            print("invlalid cookie token")

    if header_token:
        try:
            payload = jwt.decode(header_token, SECRET_KEY, algorithms=[ALGORITHM])
            print("finished trying payload??")
            username = payload.get("sub")
            user = get_user(session, username)
            if not user:
                print("no user")
            else:
                user_true = True
        except InvalidTokenError:
            print("invlalid header token")

    if user_true:
        return user
    else:
        return None


@dataclass
class HTMXContext:
    request: Request
    session: SessionDep
    current_user: UserInDB | None = None


async def get_htmx_context(request: Request, session: SessionDep,
                           current_user: Annotated[(UserInDB, Depends(get_current_user_or_none))]):
    ctx = HTMXContext(request=request, session=session, current_user=current_user)
    return ctx


def get_template_context(ctx: Annotated[HTMXContext, Depends(get_htmx_context)], *args):
    context = {}

    if ctx.current_user:
        context["current_user"] = ctx.current_user

    context.update(*args)
    return context

