import sys
import logging
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from a2wsgi import ASGIMiddleware
import uvicorn
import psycopg2  # for postgresql

from starlette.middleware.cors import CORSMiddleware

from hours_app.routers import crud_basic, crud_detailed, calendar, users
from hours_app.routers.interactions import router as interactions_router
from hours_app.database import create_db_and_tables
from hours_app.models import Sesh
from hours_app.dependencies import SessionDep


app = FastAPI(title="hours.py upgraded", swagger_ui_parameters={"persistAuthorization": True}, version="0.4")
application = ASGIMiddleware(app)

app.mount("/static", StaticFiles(directory="hours_app/static"), name="static")
# origins = [
#     'http://localhost:8000'
# ]
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# logger = logging.getLogger(__name__)
#
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
# )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    response_time = time.perf_counter() - start_time
    # logger.info(f"{request.method} {request.url.path} {response.status_code} {response_time:.3f}s OHAYO SEKAI GOODMORNING WOOOOORLD")
    return response


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
def root():
    # logger.info("rooooooot")
    return RedirectResponse(url="/docs")


@app.get("/test-msg")
def test_msg():
    return {"msg": "heya"}


app.include_router(crud_basic.router)
app.include_router(crud_detailed.router)
app.include_router(calendar.router)
app.include_router(users.router)
app.include_router(interactions_router)


if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", log_level="error")
