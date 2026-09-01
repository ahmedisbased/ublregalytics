from fastapi import HTTPException
import teradatasql

from .query_helpers import search_condition






def view_loan_type_service(
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
        DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING
        WHERE START_DATE = '{date}'
        {search_condition(search, ['SL_CODE', 'LOAN_TYPE', 'LOAN_TYPE_DESC', 'CURY_EDW_ID'])}
        QUALIFY ROW_NUMBER() OVER
		(ORDER BY LOAN_TYPE, CURY_EDW_ID) BETWEEN {start} AND {end}"""
        cursor.execute(query)
        print(query)
        rows = cursor.fetchall()       
        count_query = f"""
            SELECT COUNT(*)
            FROM DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING
            WHERE START_DATE = '{date}'
            {search_condition(search, ['SL_CODE', 'LOAN_TYPE', 'LOAN_TYPE_DESC', 'CURY_EDW_ID'])}
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


def update_loan_type_service(
        sl_code: str,
        cury_edw_id: str,
        loan_type: str,
        start_date: str,
        conn,
):

    try :
        cursor = conn.cursor()
        query = f"""
        UPDATE DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING 
        SET SL_CODE = '{sl_code}',
            UPDATE_DATE = CURRENT_DATE,
            UPDATE_TS = CURRENT_TIMESTAMP
        WHERE LOAN_TYPE = '{loan_type}'
        AND CURY_EDW_ID = '{cury_edw_id}'
        AND START_DATE = '{start_date}';

        """
        cursor.execute(query)

        query = f"""
                SELECT * FROM DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING 
                WHERE LOAN_TYPE = '{loan_type}'
                AND SL_CODE = '{sl_code}'
                AND CURY_EDW_ID = '{cury_edw_id}'
                AND START_DATE = '{start_date}';
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"rows are {rows}")
        if not rows:
            raise HTTPException(detail = "update failed, resource not found.", status_code = 404)
    except Exception as e:
            raise HTTPException(detail = {"error" : str(e)}, status_code = 503)
    
    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns,row)) for row in rows]
    return {"status" : "success",
    "message": "sl_code updated successfully",
    "data" : result}
