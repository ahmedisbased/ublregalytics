import teradatasql
from .queries import *
import pandas as pd 

class NoRecordsFound(Exception):
    """Raised when the main transaction query returns zero rows"""
    pass 


def fetch_data(account_number, transaction_id , from_date = None, to_date= None):
	
    cursor = None
    conn = None
    p_acct_no = str(account_number)
    p_trxn_no = str(transaction_id)
    p_date_from = f"'{from_date}'" if from_date else 'NULL'
    p_date_to = f"'{to_date}'" if from_date else 'NULL'
    
    # Credentials sourced from environment / .env (see app/core/config.py).
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
    print("Connection established successfully.")
    cursor = conn.cursor()

    transactions_query = get_transactions_query(p_acct_no, p_trxn_no, p_date_from, p_date_to)
    individual_data = pd.read_sql(transactions_query, conn )
    # print("Len of the columns in df: ", len(individual_data.columns))
    # individual_data.to_csv("individual_data.csv")
    # individual_data = pd.read_csv("individual_data.csv")
    # print("Len of the columns in csv: ", len(individual_data.columns))

    print(f"Length of individual_data : {len(individual_data)}")




    wallet_query = get_wallet_query2(p_acct_no)
    wallet_query_data = pd.read_sql(wallet_query, conn )
    wallet_query_data.to_csv("wallet_query_data.csv")

    print(f"Length of wallet_query : {len(wallet_query_data)}")
    wallet_query_data = pd.read_csv("wallet_query_data.csv")

    
    cbs_cc_query = get_cbs_cc_query2(p_acct_no)
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

    cursor.close()
    conn.close()

    return individual_data, wallet_query_data, cbs_cc_query_data, entity_query_data
