from sqlmodel import Session, create_engine, SQLModel

from hours_app.config import settings


engine = create_engine(settings.SQLALCHEMY_DATABASE_URL, echo=True)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

