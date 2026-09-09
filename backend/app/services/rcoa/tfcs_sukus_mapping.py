from fastapi import HTTPException
import teradatasql

from ...schemas.rcoa.metadata import table_select_list, table_search_columns
from ...schemas.rcoa.validation import is_ascii_letters
from .query_helpers import search_condition


RCOA_ADVANCES_MAPPING_TABLE = "DT_SDMT_UBL.RCOA_ADVANCES_MAPPING"


def view_tfcs_sukus_mapping_service(
    date: str,
    page: int,
    conn,
    limit: int = 20,
    search: str | None = None,
):
    try:
        cursor = conn.cursor()
        start = (page - 1) * limit + 1
        end = page * limit

        query = f"""
        SELECT {table_select_list(RCOA_ADVANCES_MAPPING_TABLE)} FROM
        {RCOA_ADVANCES_MAPPING_TABLE}
        WHERE START_DATE = '{date}'
        {search_condition(search, table_search_columns(RCOA_ADVANCES_MAPPING_TABLE, ['LOAN_NO', 'CUST_NAME', 'RCOA_CODE']))}
        QUALIFY ROW_NUMBER() OVER
        (ORDER BY LOAN_NO, CUST_NAME, RCOA_CODE) BETWEEN {start} AND {end}
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        count_query = (
            f"SELECT COUNT(*) FROM {RCOA_ADVANCES_MAPPING_TABLE} "
            f"WHERE START_DATE = '{date}' "
            f"{search_condition(search, table_search_columns(RCOA_ADVANCES_MAPPING_TABLE, ['LOAN_NO', 'CUST_NAME', 'RCOA_CODE']))}"
        )
        cursor2 = conn.cursor()
        cursor2.execute(count_query)
        total_records = cursor2.fetchone()[0]
        total_pages = max(1, (total_records + limit - 1) // limit)
    except teradatasql.DatabaseError as e:
        raise HTTPException(
            detail={"error": str(e), "message": "Database Error"},
            status_code=503,
        )
    except teradatasql.OperationalError:
        raise HTTPException(detail="Operational Error", status_code=503)
    except teradatasql.Error as e:
        raise HTTPException(
            detail={"error": str(e), "message": "Could not connect to teradata"},
            status_code=503,
        )

    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns, row)) for row in rows]
    return {
        "data": result,
        "pagination": {
            "currentPage": page,
            "pageSize": limit,
            "totalRecords": total_records,
            "totalPages": total_pages,
        },
    }


def update_tfcs_sukus_mapping_service(
    loan_no: str,
    start_date: str,
    cust_name: str | None,
    rcoa_code: str | None,
    conn,
):
    if cust_name is not None and not is_ascii_letters(cust_name):
        raise HTTPException(
            detail="Customer name must contain only letters A-Z.",
            status_code=422,
        )

    updates = []
    verification_conditions = [
        f"LOAN_NO = '{loan_no}'",
        f"START_DATE = '{start_date}'",
    ]

    if cust_name is not None:
        updates.append(f"CUST_NAME = '{cust_name}'")
        verification_conditions.append(f"CUST_NAME = '{cust_name}'")
    if rcoa_code is not None:
        updates.append(f"RCOA_CODE = '{rcoa_code}'")
        verification_conditions.append(f"RCOA_CODE = '{rcoa_code}'")

    if not updates:
        raise HTTPException(
            detail="Either cust_name or rcoa_code should not be None",
            status_code=422,
        )

    updates.append("UPDATE_DATE = CURRENT_DATE")
    updates.append("UPDATE_TS = CURRENT_TIMESTAMP")

    try:
        cursor = conn.cursor()
        query = f"""
        UPDATE {RCOA_ADVANCES_MAPPING_TABLE}
        SET {', '.join(updates)}
        WHERE LOAN_NO = '{loan_no}'
        AND START_DATE = '{start_date}'
        """
        cursor.execute(query)

        query = f"""
        SELECT {table_select_list(RCOA_ADVANCES_MAPPING_TABLE)} FROM {RCOA_ADVANCES_MAPPING_TABLE}
        WHERE {' AND '.join(verification_conditions)}
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(
                detail="update failed, resource not found.",
                status_code=404,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(detail={"error": str(e)}, status_code=503)

    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns, row)) for row in rows]
    return {
        "status": "success",
        "message": "cust_name and/or rcoa_code updated successfully",
        "data": result,
    }
