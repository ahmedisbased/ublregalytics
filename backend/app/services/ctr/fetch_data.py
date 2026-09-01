import teradatasql
from .quries import *
import pandas as pd 
import time
def fetch_data(transaction_date, cr_dr_flag, entity_individual_flag):
	
    HOST = "10.1.128.102"        # e.g., "tdprod.company.com"
    USER = "DP_GCFR_USER"
    PASSWORD = "dp_98gcfr_12user_56"
    DATABASE = "DP_SDMT_DFDN"       # optional, can be omitted
    LOG_MECH = "TD2"    
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

    if cr_dr_flag == 'CR':
        print("in CR")

        check = check_query()
        
        print(f"the query we got is this : {check}")
        check_result = pd.read_sql(check, conn)
        value_exists = check_result['STATUS'].isin(['READY'
        ]).any()
        print(f" valueeee {value_exists}")
        print(f"check result is this {check_result}")
        if not value_exists:
            return None
        
        query = get_cash_deposit_query_v2(transaction_date, entity_individual_flag )
        query_result = pd.read_sql(query, conn )


    elif cr_dr_flag == 'DR':
        print("in DR")
        check = check_query()
        print(f"the query we got is this : {check}")
        check_result = pd.read_sql(check, conn)
        value_exists = check_result['STATUS'].isin(['READY'
        ]).any()
        print(f" valueeee {value_exists}")
        print(f"check result is this {check_result}")
        if not value_exists:
            return check_result
       
        query = get_cash_withdrawal_query_v2(transaction_date, entity_individual_flag )
        query_result = pd.read_sql(query, conn)


    return query_result