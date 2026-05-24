import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import select
from a2wsgi import ASGIMiddleware
import uvicorn

from hours_app.routers import crud_basic, crud_detailed, calendar, users
from hours_app.database import create_db_and_tables
from hours_app.models import Sesh
from hours_app.dependencies import SessionDep

from dark_swag import FastAPI

app = FastAPI(title="hours.py upgraded", swagger_ui_parameters={"persistAuthorization": True})
application = ASGIMiddleware(app)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def root():
    return RedirectResponse(url="/docs_light")


app.include_router(crud_basic.router)
app.include_router(crud_detailed.router)
app.include_router(calendar.router)
app.include_router(users.router)

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", log_level="error")
