from sqlmodel import Session, create_engine, SQLModel

# THIS FILE SHOULD NOT IMPORT FROM DEPENDENCIES at the top, at least? cuz at the top of dependencies.py there's an import
# from database.py

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

