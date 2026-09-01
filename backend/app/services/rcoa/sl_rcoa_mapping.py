from fastapi import HTTPException
import teradatasql

from .query_helpers import search_condition


def view_sl_rcoa_mapping_service(
        date: str,
        page: int,
        conn,
        limit: int = 20,
        search: str | None = None,
):
    try :      
        print(f" page is {page}")
        cursor = conn.cursor()
        start = (page - 1) * limit + 1
        end = page * limit


        query = f"""
        SELECT * FROM
        DT_SDMT_UBL.SL_RCOA_MAPPING
        WHERE START_DATE = '{date}'
        {search_condition(search, ['SL_CODE', 'RCOA_CODE', 'DESCRIPTION', 'TIER', 'DOMAIN'])}
        QUALIFY ROW_NUMBER() OVER
		(ORDER BY SL_CODE, RCOA_CODE) BETWEEN {start} AND {end}"""
        cursor.execute(query)
        print(query)
        rows = cursor.fetchall()       
        count_query = f"""
            SELECT COUNT(*)
            FROM DT_SDMT_UBL.SL_RCOA_MAPPING
            WHERE START_DATE = '{date}'
            {search_condition(search, ['SL_CODE', 'RCOA_CODE', 'DESCRIPTION', 'TIER', 'DOMAIN'])}
        """
        cursor2 = conn.cursor()
        
        cursor2.execute(count_query)
        total_records = cursor2.fetchone()[0]

        total_pages = max(1, (total_records + limit - 1) // limit)
  
    except teradatasql.DatabaseError as e:
        raise HTTPException(detail = {"error" : str(e),
        "message" : "Database Error"}, status_code = 503)
    except teradatasql.OperationalError:
        raise HTTPException(detail = "Operational Error", status_code = 503)
    except teradatasql.Error as e:
        raise HTTPException(detail = {"error" : str(e),
        "message" : "Could not connect to teradata"}, status_code = 503)
    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns,row)) for row in rows]
    return {"data" : result,
    "pagination" : {
        "currentPage" : page,
        "pageSize": limit,
        "totalRecords" : total_records,
        "totalPages" : total_pages
    }
    }


def update_sl_rcoa_mapping_service(
    sl_code: str,
    rcoa_code: str | None,
    description: str | None,
    start_date: str,
    conn,
    original_rcoa_code: str | None = None,
    original_description: str | None = None,
):
    updates = []
    row_conditions = [
        f"SL_CODE = '{sl_code}'",
        f"START_DATE = '{start_date}'",
    ]
    verification_conditions = [
        f"SL_CODE = '{sl_code}'",
        f"START_DATE = '{start_date}'",
    ]

    if original_rcoa_code is not None:
        row_conditions.append(f"RCOA_CODE = '{original_rcoa_code}'")
    if original_description is not None:
        row_conditions.append(f"DESCRIPTION = '{original_description}'")

    if rcoa_code is not None:
        updates.append(f"RCOA_CODE = '{rcoa_code}'")
        verification_conditions.append(f"RCOA_CODE = '{rcoa_code}'")
    if description is not None:
        updates.append(f"DESCRIPTION = '{description}'")
        verification_conditions.append(f"DESCRIPTION = '{description}'")

    if not updates:
        raise HTTPException(
            detail="Either description or rcoa_code should not be None",
            status_code=422,
        )

    updates.append("UPDATE_DATE = CURRENT_DATE")
    updates.append("UPDATE_TS = CURRENT_TIMESTAMP")

    try:
        cursor = conn.cursor()
        query = f"""
        UPDATE DT_SDMT_UBL.SL_RCOA_MAPPING
        SET {', '.join(updates)}
        WHERE {' AND '.join(row_conditions)}
        """
        cursor.execute(query)

        query = f"""
        SELECT * FROM DT_SDMT_UBL.SL_RCOA_MAPPING
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
        "message": "rcoa_code and/or description updated successfully",
        "data": result,
    }
