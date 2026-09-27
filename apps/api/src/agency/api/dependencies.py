"""HTTP dependencies; the API layer owns transaction boundaries."""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker


def get_db(session_factory: sessionmaker[Session]):
    def dependency() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return dependency
