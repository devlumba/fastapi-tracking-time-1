from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import FastAPI, Depends, APIRouter, Query
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from pwdlib import PasswordHash
from jwt.exceptions import InvalidTokenError
from sqlmodel import select

from dark_swag import FastAPI

from ..dependencies import SessionDep
from ..models import Sesh, UserInDB, Token, TokenData, UserBase, UserCreate, UserPublic
from ..database import Session

SECRET_KEY = "f9208ed4f21b01559b9445e324694d6b7b0d48ab4bdece5364ce9cafbbb49079"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 29

password_hash = PasswordHash.recommended()  # I assume this is me choosing HOW to hash/unhash a password

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


router = APIRouter(tags=["users"])


def verify_password(plain_password, hashed_password) -> str:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(plain_password) -> str:
    return password_hash.hash(plain_password)


def get_user(session: Session, username: str) -> UserInDB:
    user = session.exec(select(UserInDB).where(UserInDB.username == username)).first()
    if user:
        return user
    else:
        print("AHHHHHHHHHHHHHHH NOOOOOOOOOOOO USERRRR OH NOOOOOOOOOOOOOOOOOOOO 500 500 500 500 500 500 500 500")


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


@router.get("/users/me")
async def read_users_me(token: Annotated[str, Depends(oauth2_scheme)],
                        current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserBase:
    return current_user


@router.post("/users/")
async def create_user(session: SessionDep,
                      username: str, password: str, confirm_password: str, full_name: str | None = None) -> UserPublic:
    user = UserCreate(username=username, password=password, full_name=full_name)
    if confirm_password != password:
        raise HTTPException(status_code=401, detail="Passwords Not Matching")
    supposed_user = session.exec(select(UserInDB).where(UserInDB.username == username)).first()
    if supposed_user:
        raise HTTPException(status_code="400", detail="This Username is Already Taken")

    hashed_password = get_password_hash(user.password)
    db_user_preval = UserInDB(username=user.username, full_name=user.full_name, hashed_password=hashed_password)
    db_user = UserInDB.model_validate(db_user_preval)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@router.get("/users/")
async def read_users_all(session: SessionDep) -> list[UserPublic]:
    users = session.exec(select(UserInDB)).all()
    return users


@router.get("/users/{username:str}")
async def read_specific_user(session: SessionDep, username: str) -> UserPublic:
    user = session.exec(select(UserInDB).where(UserInDB.username==username)).first()
    return user


@router.get("/users/me/seshs", dependencies=[Depends(oauth2_scheme)])
async def read_own_seshs(current_user: Annotated[UserInDB, Depends(get_current_user)], session: SessionDep):
    seshs = session.exec(select(Sesh).where(Sesh.owner_id==current_user.id)).all()
    return seshs


