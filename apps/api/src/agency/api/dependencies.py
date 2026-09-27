"""HTTP dependencies; the API layer owns transaction boundaries."""

from collections.abc import Callable, Generator
import logging

from sqlalchemy.orm import Session, sessionmaker


LOGGER = logging.getLogger(__name__)


def get_db(session_factory: sessionmaker[Session]):
    def dependency() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
            session.commit()
            callbacks: list[Callable[[], None]] = session.info.pop("after_commit", [])
            for callback in callbacks:
                try:
                    callback()
                except Exception:
                    LOGGER.exception("after_commit callback failed")
        except Exception:
            session.rollback()
            session.info.pop("after_commit", None)
            raise
        finally:
            session.close()

    return dependency
