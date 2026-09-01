import teradatasql
from fastapi import HTTPException

from .query_helpers import search_condition

"""
GL SL MAPPING FILE WHERE ONLY THE SL_CODE SHOULD BE CHANGED

"""
def update_gl_sl_mapping(sl_code : str, gl_edw_id : str, cury_edw_id : str, start_date : str, conn):
    try:
        cursor = conn.cursor()
      
        query = f"""
            UPDATE DT_SDMT_UBL.GL_SL_MAPPING
            SET SL_CODE = '{sl_code}',
                UPDATE_DATE = CURRENT_DATE,
                UPDATE_TS = CURRENT_TIMESTAMP
            WHERE GL_EDW_ID = '{gl_edw_id}'
            AND CURY_EDW_ID = '{cury_edw_id}'
            AND  START_DATE = '{start_date}'
        """

        cursor.execute(query)

        # making a select query to check if the update has been made or not.
        query = f"""
            SELECT * FROM DT_SDMT_UBL.GL_SL_MAPPING
            WHERE SL_CODE = '{sl_code}'
            AND GL_EDW_ID = '{gl_edw_id}'
            AND CURY_EDW_ID = '{cury_edw_id}'
            AND  START_DATE = '{start_date}'
            
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(detail = "no data returned", status_code = 404)
    except teradatasql.DatabaseError as e:
        raise HTTPException(detail = {"error" : str(e)}, status_code = 503)
    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns,row)) for row in rows]
    return {"status" : "success",
    "message": "sl_code updated successfully",
    "data" : result}

def view_gl_sl_mapping(
    date: str,
    conn,
    page: int = 1,
    limit: int = 20,
    search: str | None = None,
):
    try :      
        print(f" page is {page}")
        cursor = conn.cursor()
        start = (page - 1) * limit + 1
        end = page * limit
        query = f"""SELECT * FROM 
        DT_SDMT_UBL.GL_SL_MAPPING
        WHERE START_DATE = '{date}'
        {search_condition(search, ['GL_EDW_ID', 'GL_DESCRIPTION', 'CURY_EDW_ID', 'SL_CODE'])}
        QUALIFY ROW_NUMBER() OVER(ORDER BY GL_EDW_ID, CURY_EDW_ID) BETWEEN {start} AND {end};"""
        cursor.execute(query)
        print(query)
        rows = cursor.fetchall()       
        count_query = f"""
            SELECT COUNT(*)
            FROM DT_SDMT_UBL.GL_SL_MAPPING
            WHERE START_DATE = '{date}'
            {search_condition(search, ['GL_EDW_ID', 'GL_DESCRIPTION', 'CURY_EDW_ID', 'SL_CODE'])}
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
