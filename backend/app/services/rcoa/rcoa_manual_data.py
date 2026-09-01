from decimal import Decimal

from fastapi import HTTPException
import teradatasql

from .query_helpers import search_condition


MANUAL_DATA_SEARCH_COLUMNS = [
    '"Flag"',
    'RCOA_CODE',
    '"Domain"',
    'AMOUNT',
    '"Tier"',
    '"Particulars"',
    '"Particulars_definition"',
]


def view_rcoa_manual_data_service(
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
        DT_SDMT_UBL.RCOA_MANUAL_DATA
        WHERE START_DATE = '{date}'
        {search_condition(search, MANUAL_DATA_SEARCH_COLUMNS)}
        QUALIFY ROW_NUMBER() OVER
        (ORDER BY RCOA_CODE, "Domain", "Tier") BETWEEN {start} AND {end}
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        count_query = (
            "SELECT COUNT(*) FROM DT_SDMT_UBL.RCOA_MANUAL_DATA "
            f"WHERE START_DATE = '{date}' "
            f"{search_condition(search, MANUAL_DATA_SEARCH_COLUMNS)}"
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


def update_rcoa_manual_data_service(
    rcoa_code: str,
    start_date: str,
    amount: Decimal | None,
    domain: str | None,
    tier: str | None,
    conn,
    original_domain: str | None = None,
    original_tier: str | None = None,
):
    updates = []
    row_conditions = [
        f"RCOA_CODE = '{rcoa_code}'",
        f"START_DATE = '{start_date}'",
    ]
    verification_conditions = [
        f"RCOA_CODE = '{rcoa_code}'",
        f"START_DATE = '{start_date}'",
    ]

    if original_domain is not None:
        row_conditions.append(f'"Domain" = \'{original_domain}\'')
    if original_tier is not None:
        row_conditions.append(f'"Tier" = \'{original_tier}\'')

    if amount is not None:
        amount_value = format(amount, "f")
        updates.append(f"AMOUNT = {amount_value}")
        verification_conditions.append(f"AMOUNT = {amount_value}")
    if domain is not None:
        updates.append(f'"Domain" = \'{domain}\'')
        verification_conditions.append(f'"Domain" = \'{domain}\'')
    if tier is not None:
        updates.append(f'"Tier" = \'{tier}\'')
        verification_conditions.append(f'"Tier" = \'{tier}\'')

    if not updates:
        raise HTTPException(
            detail="At least one of amount, domain, or tier should not be None",
            status_code=422,
        )

    updates.append("UPDATE_DATE = CURRENT_DATE")
    updates.append("UPDATE_TS = CURRENT_TIMESTAMP")

    try:
        cursor = conn.cursor()
        query = f"""
        UPDATE DT_SDMT_UBL.RCOA_MANUAL_DATA
        SET {', '.join(updates)}
        WHERE {' AND '.join(row_conditions)}
        """
        cursor.execute(query)

        query = f"""
        SELECT * FROM DT_SDMT_UBL.RCOA_MANUAL_DATA
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
        "message": "amount, domain and/or tier updated successfully",
        "data": result,
    }
