from decimal import Decimal

from fastapi import HTTPException
import teradatasql

from .query_helpers import search_condition


def view_adjustments_format_service(
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
        SELECT * FROM
        DT_SDMT_UBL.RCOA_SL_WISE_ADJ
        WHERE START_DATE = '{date}'
        {search_condition(search, ['SL_CODE', 'AMOUNT', 'FLAG'])}
        QUALIFY ROW_NUMBER() OVER
        (ORDER BY SL_CODE, AMOUNT, FLAG) BETWEEN {start} AND {end}
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        count_query = (
            "SELECT COUNT(*) FROM DT_SDMT_UBL.RCOA_SL_WISE_ADJ "
            f"WHERE START_DATE = '{date}' "
            f"{search_condition(search, ['SL_CODE', 'AMOUNT', 'FLAG'])}"
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


def update_adjustments_format_service(
    start_date: str,
    sl_code: str | None,
    amount: Decimal | None,
    flag: str | None,
    conn,
    original_sl_code: str | None = None,
    original_amount: Decimal | None = None,
    original_flag: str | None = None,
):
    updates = []
    row_conditions = [f"START_DATE = '{start_date}'"]
    print(f"inside adjustments format")
    verification_conditions = [f"START_DATE = '{start_date}'"]

    try:
        if original_sl_code is not None:
            row_conditions.append(f"SL_CODE = '{original_sl_code}'")
        if original_amount is not None:
            row_conditions.append(f"AMOUNT = {format(original_amount, 'f')}")
        if original_flag is not None:
            row_conditions.append(f"FLAG = '{original_flag}'")

        if sl_code is not None:
            updates.append(f"SL_CODE = '{sl_code}'")
            verification_conditions.append(f"SL_CODE = '{sl_code}'")
        if amount is not None:
            amount_value = format(amount, "f")
            updates.append(f"AMOUNT = {amount_value}")
            verification_conditions.append(f"AMOUNT = {amount_value}")
        if flag is not None:
            updates.append(f"FLAG = '{flag}'")
            verification_conditions.append(f"FLAG = '{flag}'")

        if not updates:
            raise HTTPException(
                detail="At least one of sl_code, amount, or flag should not be None",
                status_code=422,
            )

        updates.append("UPDATE_DATE = CURRENT_DATE")
        updates.append("UPDATE_TS = CURRENT_TIMESTAMP")

        cursor = conn.cursor()
        query = f"""
        UPDATE DT_SDMT_UBL.RCOA_SL_WISE_ADJ
        SET {', '.join(updates)}
        WHERE {' AND '.join(row_conditions)}
        """
        cursor.execute(query)

        query = f"""
        SELECT * FROM DT_SDMT_UBL.RCOA_SL_WISE_ADJ
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
        "message": "sl_code, amount and/or flag updated successfully",
        "data": result,
    }
