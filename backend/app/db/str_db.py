"""Teradata connection pool used by the STR reporting pipeline."""

import logging

import teradatasql
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from app.core import config as app_config


logger = logging.getLogger(__name__)

_connection_config = {
    "host": app_config.TERADATA_HOST,
    "user": app_config.TERADATA_USER,
    "password": app_config.TERADATA_PASSWORD,
    "logmech": app_config.TERADATA_LOGMECH,
    "database": app_config.TERADATA_DATABASE,
}


def _connect():
    logger.info("Opening a new STR Teradata connection for the pool")
    return teradatasql.connect(**_connection_config)


str_engine = create_engine(
    "teradatasql://",
    creator=_connect,
    poolclass=QueuePool,
    pool_size=app_config.TERADATA_POOL_SIZE,
    max_overflow=0,
    pool_timeout=app_config.TERADATA_POOL_TIMEOUT_SECONDS,
    pool_recycle=app_config.TERADATA_POOL_RECYCLE_SECONDS,
    pool_pre_ping=True,
)


def get_str_connection():
    """Check out a pooled DBAPI connection for one STR request."""
    return str_engine.raw_connection()


def close_str_pool() -> None:
    """Close idle STR connections during application shutdown."""
    str_engine.dispose()
