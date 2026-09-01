import teradatasql
from fastapi import HTTPException


def start_reporting(date: str, user_id : str, conn):
    print(f" got the date as {date} , and the user_id is {user_id}")
    cursor = None
    try:
        cursor = conn.cursor()
        print(f"cursor made")
        query = f"CALL DT_Sdmt_ubl.SP_RCOA('{date}','{user_id}')"
        print (query)
        cursor.execute(query)
    except teradatasql.Error as e:
        print(f"the error message is {str(e)}")
        raise HTTPException(status_code = 403, detail = {"error" : "permission denied",
        "message" : "The current user does not have priveleges to call the procedure"})
    
    except Exception as e:
        raise HTTPException(status_code =500, detail = f"unexpected error: {str(e)}")
    # print(f"rows are {rows}")
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
    return 1

def end_reporting(date: str, user_id : str, conn):
    print(f" got the date as {date} , and the user_id is {user_id}")
    cursor = None
    try:
        cursor = conn.cursor()
        print(f"cursor made")
        query = f"CALL DT_SDMT_UBL.RCOA_SBP_REPORT_SP('{date}','{user_id}')"
        print (query)
        cursor.execute(query)
    except teradatasql.Error as e:
        print(f"the error message is {str(e)}")
        raise HTTPException(status_code = 403, detail = {"error" : "permission denied",
        "message" : "The current user does not have priveleges to call the procedure"})
    
    except Exception as e:
        raise HTTPException(status_code =500, detail = f"unexpected error: {str(e)}")
    # print(f"rows are {rows}")
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
    return 1
