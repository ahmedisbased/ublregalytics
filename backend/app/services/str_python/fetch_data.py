import logging
from collections.abc import Callable
from typing import Any

import pandas as pd

from app.db import get_str_connection
from .errors import NoRecordsFound, StrGenerationError, StrProcessingError, StrTeradataError
from .observability import add_str_log, exception_text, mask_account
from .queries import (
    get_cbs_cc_query2,
    get_entity_detail_query,
    get_entity_query3,
    get_transactions_query2,
    get_wallet_query2,
)


logger = logging.getLogger(__name__)


def _run_query(
    query_name: str,
    query_builder: Callable[[], str],
    conn: Any,
    logs: list[dict[str, Any]],
) -> pd.DataFrame:
    add_str_log(logs, logger, "INFO", query_name, "Building query.")
    try:
        query = query_builder()
    except Exception as error:
        add_str_log(
            logs,
            logger,
            "ERROR",
            query_name,
            "Query construction failed before it reached Teradata.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrProcessingError(f"{query_name}_build", error) from error

    add_str_log(
        logs,
        logger,
        "INFO",
        query_name,
        "Executing query on Teradata.",
        {"query_length": len(query)},
    )
    try:
        dataframe = pd.read_sql(query, conn)
    except Exception as error:
        add_str_log(
            logs,
            logger,
            "ERROR",
            query_name,
            "Teradata query execution failed.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrTeradataError(query_name, error) from error

    add_str_log(
        logs,
        logger,
        "INFO",
        query_name,
        "Teradata query completed.",
        {"rows": len(dataframe), "columns": len(dataframe.columns)},
    )
    return dataframe


def _cache_dataframe(
    dataframe: pd.DataFrame,
    filename: str,
    stage: str,
    logs: list[dict[str, Any]],
) -> pd.DataFrame:
    """Preserve the existing cache behavior and make local I/O failures explicit."""
    try:
        dataframe.to_csv(filename)
        cached = pd.read_csv(filename)
    except Exception as error:
        add_str_log(
            logs,
            logger,
            "ERROR",
            stage,
            "Local STR data cache failed after the Teradata query completed.",
            {
                "filename": filename,
                "error_type": error.__class__.__name__,
                "error": exception_text(error),
            },
        )
        raise StrProcessingError(stage, error) from error

    add_str_log(
        logs,
        logger,
        "INFO",
        stage,
        "Local STR data cache completed.",
        {"filename": filename, "rows": len(cached)},
    )
    return cached


def fetch_data(
    account_number,
    transaction_id,
    from_date=None,
    to_date=None,
    logs: list[dict[str, Any]] | None = None,
):
    cursor = None
    conn = None
    p_acct_no = str(account_number)
    p_trxn_no = str(transaction_id)
    p_date_from = f"'{from_date}'" if from_date else "NULL"
    p_date_to = f"'{to_date}'" if to_date else "NULL"
    request_logs = logs if logs is not None else []

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "data_fetch",
        "Starting STR data retrieval.",
        {
            "account": mask_account(account_number),
            "transaction_filter": bool(p_trxn_no),
            "from_date": from_date or "not set",
            "to_date": to_date or "not set",
        },
    )

    # Teradata credentials come from the environment / .env. The connection
    # itself is checked out from the shared STR pool below.
    from app.core import config as app_config

    host = app_config.TERADATA_HOST
    database = app_config.TERADATA_DATABASE
    log_mech = app_config.TERADATA_LOGMECH

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "teradata_connection",
        "Connecting to Teradata.",
        {
            "host": host,
            "database": database,
            "log_mechanism": log_mech,
            "pool_size": app_config.TERADATA_POOL_SIZE,
        },
    )
    try:
        conn = get_str_connection()
        cursor = conn.cursor()
    except Exception as error:
        add_str_log(
            request_logs,
            logger,
            "ERROR",
            "teradata_connection",
            "Teradata connection failed.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrTeradataError("teradata_connection", error) from error

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "teradata_connection",
        "Teradata connection established.",
    )

    try:
        transaction_data = _run_query(
            "transactions_query",
            lambda: get_transactions_query2(p_acct_no, p_trxn_no, p_date_from, p_date_to),
            conn,
            request_logs,
        )
        if transaction_data is None or transaction_data.empty:
            add_str_log(
                request_logs,
                logger,
                "WARNING",
                "transactions_query",
                "Teradata returned no transaction rows for the supplied criteria.",
            )
            raise NoRecordsFound()

        wallet_query_data = _run_query(
            "wallet_query",
            lambda: get_wallet_query2(p_acct_no),
            conn,
            request_logs,
        )
        wallet_query_data = _cache_dataframe(
            wallet_query_data,
            "wallet_query_data.csv",
            "wallet_cache",
            request_logs,
        )

        cbs_cc_query_data = _run_query(
            "cbs_cc_query",
            lambda: get_cbs_cc_query2(p_acct_no),
            conn,
            request_logs,
        )
        cbs_cc_query_data = _cache_dataframe(
            cbs_cc_query_data,
            "cbs_cc_query_data.csv",
            "cbs_cc_cache",
            request_logs,
        )

        entity_query_data = _run_query(
            "entity_query",
            lambda: get_entity_query3(p_acct_no),
            conn,
            request_logs,
        )
        entity_query_data = _cache_dataframe(
            entity_query_data,
            "entity_query_data.csv",
            "entity_cache",
            request_logs,
        )

        entity_detail_data = _run_query(
            "entity_detail_query",
            lambda: get_entity_detail_query(p_acct_no),
            conn,
            request_logs,
        )
        entity_detail_data = _cache_dataframe(
            entity_detail_data,
            "entity_detail_data.csv",
            "entity_detail_cache",
            request_logs,
        )

        add_str_log(
            request_logs,
            logger,
            "INFO",
            "data_fetch",
            "All STR datasets loaded successfully.",
            {
                "transactions": len(transaction_data),
                "wallet_rows": len(wallet_query_data),
                "cbs_rows": len(cbs_cc_query_data),
                "entity_rows": len(entity_query_data),
                "entity_detail_rows": len(entity_detail_data),
            },
        )
        return transaction_data, wallet_query_data, cbs_cc_query_data, entity_query_data, entity_detail_data
    except StrTeradataError:
        if conn is not None:
            try:
                conn.invalidate()
                add_str_log(
                    request_logs,
                    logger,
                    "WARNING",
                    "teradata_connection",
                    "Broken Teradata connection invalidated instead of returning to the pool.",
                )
            except Exception as error:
                add_str_log(
                    request_logs,
                    logger,
                    "WARNING",
                    "teradata_connection",
                    "Could not invalidate the broken Teradata connection.",
                    {"error_type": error.__class__.__name__, "error": exception_text(error)},
                )
        raise
    except StrGenerationError:
        raise
    except Exception as error:
        add_str_log(
            request_logs,
            logger,
            "ERROR",
            "data_fetch",
            "Unexpected STR data preparation failure.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrProcessingError("data_fetch", error) from error
    finally:
        if cursor is not None:
            try:
                cursor.close()
                add_str_log(
                    request_logs,
                    logger,
                    "INFO",
                    "teradata_connection",
                    "Teradata cursor closed.",
                )
            except Exception as error:
                add_str_log(
                    request_logs,
                    logger,
                    "WARNING",
                    "teradata_connection",
                    "Teradata cursor could not be closed cleanly.",
                    {"error_type": error.__class__.__name__, "error": exception_text(error)},
                )
        if conn is not None:
            try:
                conn.close()
                add_str_log(
                    request_logs,
                    logger,
                    "INFO",
                    "teradata_connection",
                    "STR Teradata connection returned to the pool.",
                )
            except Exception as error:
                add_str_log(
                    request_logs,
                    logger,
                    "WARNING",
                    "teradata_connection",
                    "Teradata connection could not be closed cleanly.",
                    {"error_type": error.__class__.__name__, "error": exception_text(error)},
                )
