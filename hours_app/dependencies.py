from typing import Annotated

from sqlmodel import Session
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.exceptions import HTTPException
import jwt
from jwt.exceptions import InvalidTokenError

from hours_app.database import get_session
from hours_app.models import UserInDB, TokenData


SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# circular import
from .routers.users import get_current_user, get_user, SECRET_KEY, ALGORITHM
UserDep = Annotated[UserInDB, Depends(get_current_user)]

