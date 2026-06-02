from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
import jwt
from jwt.exceptions import InvalidTokenError, PyJWTError
from sqlmodel import select

from hours_app.database import get_session
from hours_app.models import UserInDB, TokenData
from hours_app.routers.users import get_current_user, get_user, SECRET_KEY, ALGORITHM
from hours_app.dependencies import SessionDep, oauth2_scheme


def token_decode(token: str):
    if not token:
        return None
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    return username

def get_current_user_or_none(session: SessionDep, request: Request) -> UserInDB:
    token = request.cookies.get("access_token")
    # print(token)
    if not token:
        print("no bueno")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user = get_user(session, username)
        if not user:
            print("no user")
            return None
    except InvalidTokenError:
        print("invlalid token")
        return None

    return user
