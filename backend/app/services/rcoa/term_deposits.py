from fastapi import HTTPException
import teradatasql

from .query_helpers import search_condition

def update_term_deposits(gl_edw_id : str, sl_code : str, cury_edw_id : str, dep_term_prd : str,
                        dep_term_type : str, start_date : str, conn):
    try :
        cursor = conn.cursor()
        query = f"""
        
        UPDATE DT_SDMT_UBL.RCOA_TD_MAPPING 
        SET SL_CODE = '{sl_code}',
            UPDATE_DATE = CURRENT_DATE,
            UPDATE_TS = CURRENT_TIMESTAMP
        WHERE GL_EDW_ID = '{gl_edw_id}'
        AND CURY_EDW_ID = '{cury_edw_id}'
        AND DEP_TERM_TYPE = '{dep_term_type}'
        AND DEP_TERM_PRD = '{dep_term_prd}'
        AND START_DATE = '{start_date}'
        
        """
        cursor.execute(query)

        query = f"""
                SELECT * FROM DT_SDMT_UBL.RCOA_TD_MAPPING 
                WHERE SL_CODE = '{sl_code}'
                AND GL_EDW_ID = '{gl_edw_id}'
                AND CURY_EDW_ID = '{cury_edw_id}'
                AND DEP_TERM_TYPE = '{dep_term_type}'
                AND DEP_TERM_PRD = '{dep_term_prd}'
                AND START_DATE = '{start_date}'
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




def view_term_deposits(
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
        DT_SDMT_UBL.RCOA_TD_MAPPING
        WHERE START_DATE = '{date}'
        {search_condition(search, ['GL_EDW_ID', 'CURY_EDW_ID', 'SL_CODE', 'DEP_TERM_TYPE', 'DEP_TERM_PRD'])}
        QUALIFY ROW_NUMBER() OVER(ORDER BY GL_EDW_ID, CURY_EDW_ID, DEP_TERM_PRD, DEP_TERM_TYPE) BETWEEN {start} AND {end};"""
        cursor.execute(query)
        print(query)
        rows = cursor.fetchall()       
        count_query = f"""
            SELECT COUNT(*)
            FROM DT_SDMT_UBL.RCOA_TD_MAPPING
            WHERE START_DATE = '{date}'
            {search_condition(search, ['GL_EDW_ID', 'CURY_EDW_ID', 'SL_CODE', 'DEP_TERM_TYPE', 'DEP_TERM_PRD'])}
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

