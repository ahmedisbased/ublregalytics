import logging

import teradatasql
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from app.core import config as app_config


logger = logging.getLogger(__name__)

HOST = app_config.TD_HOST
USER = app_config.TD_USER
PASSWORD = app_config.TD_PASSWORD
DATABASE = app_config.TD_DATABASE
LOG_MECH = app_config.TD_LOGMECH
# Build connection configuration
config = {
        "host": HOST,
        "user": USER,
        "password": PASSWORD,
        "logmech": LOG_MECH,
        "database": DATABASE,   # optional
    }


def _connect():
    return teradatasql.connect(**config)


# Keep a small pool of authenticated sessions so each RCOA request can reuse
# an existing Teradata connection instead of reconnecting from scratch.
engine = create_engine(
    "teradatasql://",
    creator=_connect,
    poolclass=QueuePool,
    pool_size=app_config.TD_POOL_SIZE,
    max_overflow=0,
    pool_timeout=app_config.TD_POOL_TIMEOUT_SECONDS,
    pool_recycle=app_config.TD_POOL_RECYCLE_SECONDS,
)



def get_db():
    conn = None
    try:
        conn = engine.raw_connection()
        yield conn
    except teradatasql.Error as exc:
        invalidate = getattr(conn, "invalidate", None)
        if callable(invalidate):
            invalidate()
        logger.exception("Teradata connection failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database unavailable",
                "message": "Could not connect to Teradata. Check the network or VPN connection.",
            },
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Teradata connection pool failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": str(exc),
                "message": "No Teradata connection is available right now. Try again shortly.",
            },
        ) from exc
    finally:
        if conn is not None:
            conn.close()


def close_db_pool():
    engine.dispose()

