from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import select

from .routers import crud_basic, crud_detailed, calendar, users
from .database import create_db_and_tables
from .models import Sesh
from .dependencies import SessionDep

from dark_swag import FastAPI

app = FastAPI(title="hours.py upgraded")


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def root():
    return RedirectResponse(url="/docs_light")


@app.get("/seshs/", tags=["crud"])
def read_seshs(session: SessionDep):
    seshs = session.exec(select(Sesh)).all()
    return seshs



app.include_router(crud_basic.router)
app.include_router(crud_detailed.router)
app.include_router(calendar.router)
app.include_router(users.router)


@app.get("/")
async def root():
    return RedirectResponse("/docs_light")

