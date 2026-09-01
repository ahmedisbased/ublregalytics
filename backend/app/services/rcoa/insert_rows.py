from datetime import date
from decimal import Decimal
import logging
import re

import teradatasql
from fastapi import HTTPException


logger = logging.getLogger(__name__)


def _sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _date_values(start_date: str) -> tuple[str, str]:
    try:
        normalized_date = date.fromisoformat(start_date).isoformat()
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="start_date must be a valid date in YYYY-MM-DD format.",
        ) from exc

    escaped_date = _sql_text(normalized_date)
    return (
        # Convert through DATE so Teradata supplies the midnight time portion
        # instead of parsing a date-only string as a full timestamp.
        f"CAST(CAST({escaped_date} AS DATE) AS TIMESTAMP(6))",
        f"CAST({escaped_date} AS DATE)",
    )


def _rollback(conn) -> None:
    rollback = getattr(conn, "rollback", None)
    if not callable(rollback):
        return
    try:
        rollback()
    except Exception:
        logger.warning("Could not roll back the failed RCOA insert transaction.", exc_info=True)


def _raise_insert_error(conn, table: str, columns: list[str], exc: Exception):
    _rollback(conn)
    error_text = str(exc).strip() or exc.__class__.__name__
    error_code_match = re.search(r"\[Error\s+(\d+)\]", error_text, re.IGNORECASE)
    error_code = int(error_code_match.group(1)) if error_code_match else None

    if error_code == 6760 or "invalid timestamp" in error_text.lower():
        status_code = 422
        message = "Teradata rejected the timestamp. RCOA dates must use YYYY-MM-DD format."
    elif isinstance(exc, teradatasql.IntegrityError):
        status_code = 409
        message = "The row conflicts with an existing record or database constraint."
    elif error_code is not None and "[Teradata Database]" in error_text:
        # Teradata reports statement/data failures, including syntax errors,
        # through OperationalError in some driver versions.
        status_code = 422
        message = "Teradata rejected the row. Check the values and table definition."
    elif isinstance(exc, (teradatasql.OperationalError, teradatasql.InterfaceError)):
        status_code = 503
        message = "Teradata is unavailable while processing the insert."
    elif isinstance(exc, (
        teradatasql.DataError,
        teradatasql.ProgrammingError,
        teradatasql.DatabaseError,
        teradatasql.Error,
    )):
        status_code = 422
        message = "Teradata rejected the row. Check the values and table definition."
    else:
        status_code = 500
        message = "The RCOA row could not be inserted because of an unexpected server error."

    logger.exception(
        "RCOA insert failed for table=%s columns=%s status=%s: %s",
        table,
        ", ".join(columns),
        status_code,
        error_text,
    )
    raise HTTPException(
        detail={
            "message": message,
            "error": error_text,
            "table": table,
        },
        status_code=status_code,
    ) from exc


def _insert_row(
    conn,
    table: str,
    columns: list[str],
    values: list[str],
    message: str,
):
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(values)})"
        )

        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()

        return {
            "status": "success",
            "message": message,
            # The frontend refreshes the current page after the commit. Avoid
            # another Teradata round trip just to rebuild a row it does not use.
            "data": [],
        }
    except HTTPException:
        raise
    except teradatasql.Error as exc:
        _raise_insert_error(conn, table, columns, exc)
    except Exception as exc:
        _raise_insert_error(conn, table, columns, exc)
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass


def insert_adjustments_format(
    start_date: str,
    sl_code: str,
    amount: Decimal,
    flag: str,
    conn,
):
    start_timestamp, start_date_value = _date_values(start_date)
    return _insert_row(
        conn=conn,
        table="DT_SDMT_UBL.RCOA_SL_WISE_ADJ",
        columns=[
            "SL_CODE",
            "AMOUNT",
            "FLAG",
            "START_TS",
            "END_TS",
            "UPDATE_TS",
            "START_DATE",
            "END_DATE",
            "UPDATE_DATE",
            "RECORD_DELETED_FLAG",
            "SYSTEM_CODE",
            "PROCESS_NAME",
            "UPDATE_PROCESS_NAME",
            "ROW_HASH",
        ],
        values=[
            _sql_text(sl_code),
            format(amount, "f"),
            _sql_text(flag),
            start_timestamp,
            start_timestamp,
            start_timestamp,
            start_date_value,
            start_date_value,
            start_date_value,
            "'0'",
            "'CBS'",
            "'SP_RCOA'",
            "'SP_RCOA'",
            "'SP_RCOA'",
        ],
        message="Adjustment row inserted successfully.",
    )


def insert_rcoa_manual_data(
    start_date: str,
    rcoa_code: str,
    domain: str,
    tier: str,
    amount: Decimal,
    flag: str,
    particulars: str,
    particulars_definition: str,
    conn,
):
    start_timestamp, start_date_value = _date_values(start_date)
    return _insert_row(
        conn=conn,
        table="DT_SDMT_UBL.RCOA_MANUAL_DATA",
        columns=[
            "RCOA_CODE",
            '"Domain"',
            '"Tier"',
            "AMOUNT",
            '"Flag"',
            '"Particulars"',
            '"Particulars_definition"',
            "START_TS",
            "END_TS",
            "UPDATE_TS",
            "START_DATE",
            "END_DATE",
            "UPDATE_DATE",
            "RECORD_DELETED_FLAG",
            "SYSTEM_CODE",
            "PROCESS_NAME",
            "UPDATE_PROCESS_NAME",
            "ROW_HASH",
        ],
        values=[
            _sql_text(rcoa_code),
            _sql_text(domain),
            _sql_text(tier),
            format(amount, "f"),
            _sql_text(flag),
            _sql_text(particulars),
            _sql_text(particulars_definition),
            start_timestamp,
            start_timestamp,
            start_timestamp,
            start_date_value,
            start_date_value,
            start_date_value,
            "'0'",
            "'CBS'",
            "'SP_RCOA'",
            "'SP_RCOA'",
            "'SP_RCOA'",
        ],
        message="Manual RCOA row inserted successfully.",
    )


def insert_tfcs_sukus(
    start_date: str,
    loan_no: str,
    cust_name: str,
    rcoa_code: str,
    conn,
):
    start_timestamp, start_date_value = _date_values(start_date)
    return _insert_row(
        conn=conn,
        table="DT_SDMT_UBL.RCOA_ADVANCES_MAPPING",
        columns=[
            "LOAN_NO",
            "CUST_NAME",
            "RCOA_CODE",
            "START_TS",
            "END_TS",
            "UPDATE_TS",
            "START_DATE",
            "END_DATE",
            "UPDATE_DATE",
            "RECORD_DELETED_FLAG",
            "SYSTEM_CODE",
            "PROCESS_NAME",
            "UPDATE_PROCESS_NAME",
            "ROW_HASH",
        ],
        values=[
            _sql_text(loan_no),
            _sql_text(cust_name),
            _sql_text(rcoa_code),
            start_timestamp,
            start_timestamp,
            start_timestamp,
            start_date_value,
            start_date_value,
            start_date_value,
            "'0'",
            "'CBS'",
            "'SP_RCOA'",
            "'SP_RCOA'",
            "'SP_RCOA'",
        ],
        message="TFC/Sukuk row inserted successfully.",
    )
