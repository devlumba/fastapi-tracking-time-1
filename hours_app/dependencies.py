from typing import Annotated

from sqlmodel import Session
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from .database import get_session
from .models import UserInDB

SessionDep = Annotated[Session, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# circular import
from .routers.users import get_current_user
UserDep = Annotated[UserInDB, Depends(get_current_user)]


