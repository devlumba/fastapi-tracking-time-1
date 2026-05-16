from datetime import date, timedelta

from enum import Enum
from sqlmodel import SQLModel, Field, ForeignKey
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserBase(SQLModel):  # i could return disabled functionality at some point
    username: str = Field(index=True)
    full_name: str | None = Field()


class UserInDB(UserBase, table=True):
    __tablename__ = "user_table"
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    id: int


class SeshType(Enum):  # i could probably make SeshType just a string? or take values from a list?
    duolingo = "duolingo"
    programming = "programming"
    words = "words"
    reading = "reading"
    juggling = "juggling"


class SeshBase(SQLModel):
    length: int | None = Field(default=None, index=True)
    specifics: str = Field()
    day: date = Field(index=True, default_factory=date.today)
    sub_tag_one: str | None = Field(index=True, default=None)
    sub_tag_two: str | None = Field(index=True, default=None)



class Sesh(SeshBase, table=True):  # == SeshInDB
    __tablename__ = "sesh_table"
    id: int | None = Field(default=None, primary_key=True)
    type: SeshType | None = Field(index=True, default=None)  # this can be in the SeshBase?
    owner_id: int | None = Field(default=None, foreign_key="user_table.id")


class SeshCreate(SeshBase):
    pass


class SeshUpdate(SeshBase):
    length: int | None = None
    specifics: str | None = None
    day: date | None = None
    type: SeshType | None = None
