"""HTTP dependencies; the API layer owns transaction boundaries."""

from collections.abc import Callable, Generator
import logging

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker


LOGGER = logging.getLogger(__name__)


def get_db(session_factory: sessionmaker[Session]):
    def dependency(request: Request) -> Generator[Session, None, None]:
        session = session_factory()
        sessions = getattr(request.state, "db_sessions", None)
        if sessions is None:
            sessions = []
            request.state.db_sessions = sessions
        sessions.append(session)
        session.info["api_transaction_failed"] = False
        session.info["api_transaction_committed"] = False
        try:
            yield session
        except Exception:
            session.rollback()
            session.info["api_transaction_failed"] = True
            session.info.pop("after_commit", None)
            raise
        finally:
            if not session.info["api_transaction_failed"] and not session.info["api_transaction_committed"]:
                try:
                    session.commit()
                    session.info["api_transaction_committed"] = True
                except Exception:
                    session.rollback()
                    session.info["api_transaction_failed"] = True
                    session.info.pop("after_commit", None)
                    raise
            if not session.info["api_transaction_failed"]:
                callbacks: list[Callable[[], None]] = session.info.pop("after_commit", [])
                for callback in callbacks:
                    try:
                        callback()
                    except Exception:
                        LOGGER.exception("after_commit callback failed")
            session.close()
            session.info["api_transaction_closed"] = True

    return dependency
