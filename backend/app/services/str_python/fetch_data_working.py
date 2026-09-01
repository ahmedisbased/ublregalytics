import teradatasql
from .queries import *
import pandas as pd 
import logging

print("loaded file")
class NoRecordsFound(Exception):    
    """Raised when no records found"""
    pass 

def fetch_data(account_number, transaction_id , from_date = None, to_date= None):
	
    cursor = None
    conn = None
    p_acct_no = str(account_number)
    p_trxn_no = str(transaction_id)
    p_date_from = f"'{from_date}'" if from_date else 'NULL'
    p_date_to = f"'{to_date}'" if from_date else 'NULL'
    
    # Teradata credentials now come from environment / .env (see app/core/config.py)
    # instead of being hardcoded in source. Do NOT commit real credentials.
    from app.core import config as app_config

    HOST = app_config.TERADATA_HOST
    USER = app_config.TERADATA_USER
    PASSWORD = app_config.TERADATA_PASSWORD
    DATABASE = app_config.TERADATA_DATABASE
    LOG_MECH = app_config.TERADATA_LOGMECH
    # Build connection configuration
    config = {
        "host": HOST,
        "user": USER,
        "password": PASSWORD,
        "logmech": LOG_MECH,
        "database": DATABASE,   # optional
    }

    print(f"Connecting to Teradata at {HOST}...")
    conn = teradatasql.connect(**config)
    if conn:
        print(f"conn is {conn}")
        print("Connection established successfully.")
    
    cursor = conn.cursor()

    transactions_query = get_transactions_query2(p_acct_no, p_trxn_no, p_date_from, p_date_to)
    print(transactions_query)

    transaction_data = pd.read_sql(transactions_query, conn )
    print(f"Length of transaction_data : {len(transaction_data)}")

    if transaction_data is None or transaction_data.empty:
        logging.info(f"Completed query execution for account number {main_account}")

        raise NoRecordsFound
    




    wallet_query = get_wallet_query2(p_acct_no)
    wallet_query_data = pd.read_sql(wallet_query, conn )
    wallet_query_data.to_csv("wallet_query_data.csv")

    print(f"Length of wallet_query : {len(wallet_query_data)}")
    wallet_query_data = pd.read_csv("wallet_query_data.csv")

    
    cbs_cc_query = get_cbs_cc_query2(p_acct_no)
    print("CBS_QUERY \n", cbs_cc_query)
    cbs_cc_query_data = pd.read_sql(cbs_cc_query, conn )
    # print(f"Length of cbs_cc_query_DATA : {len(cbs_cc_query_data)}")
    cbs_cc_query_data.to_csv("cbs_cc_query_data.csv")
    cbs_cc_query_data = pd.read_csv("cbs_cc_query_data.csv")


    # individual_complete_data = pd.concat([wallet_query_data, cbs_cc_query_data], ignore_index = True)
    # print("len of combinmed: ", len(individual_complete_data))
    # # pd.to_csv(individual_complete_data, "individual_complete_data.csv")
    # individual_complete_data.to_csv("individual_complete_data.csv")



    entity_query = get_entity_query3(p_acct_no)
    entity_query_data = pd.read_sql(entity_query, conn )
    # print(f"Length of entity_query_data : {len(entity_query_data)}")
    entity_query_data.to_csv("entity_query_data.csv")
    entity_query_data = pd.read_csv("entity_query_data.csv")


    # 5th query: Entity detail (MAIN_CLIENT, DIRECTOR_CLIENT, MANDATE_CLIENT)
    # Used for populating TFMC/TTMC entity account blocks with director/mandate info
    entity_detail_query = get_entity_detail_query(p_acct_no)
    entity_detail_data = pd.read_sql(entity_detail_query, conn)
    entity_detail_data.to_csv("entity_detail_data.csv")
    entity_detail_data = pd.read_csv("entity_detail_data.csv")
    print(f"Length of entity_detail_data : {len(entity_detail_data)}")





    cursor.close()
    conn.close()

    return transaction_data, wallet_query_data, cbs_cc_query_data, entity_query_data, entity_detail_data
