"""SQLite engine/session factory with v1 reliability pragmas."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str = "sqlite:///agency.db") -> sessionmaker[Session]:
    engine = create_engine(database_url, future=True)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_all(database_url: str = "sqlite:///agency.db") -> None:
    from agency.db.base import Base
    from agency.db import auth_models  # noqa: F401
    from agency.db import models  # noqa: F401

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    engine.dispose()
