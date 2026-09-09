import pandas as pd
import os
import logging
from fastapi import File, Form, UploadFile
import json
import io
from ....schemas import CTRData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
CTR XML Generator
=================
Converts Excel query output into goAML-compliant XML for CTR reporting.

Supports four cases:
  1. entity_deposit        - Entity in TO account, person in FROM
  2. entity_withdrawal     - Entity in FROM account, person in TO
  3. individual_deposit    - Individual account in TO, person in FROM
  4. individual_withdrawal - Individual account in FROM, person in TO

Usage:
  python ctr_xml_generator.py <case> <excel_file> <output_xml>
"""

from datetime import datetime
import sys
import os
import json
import pandas as pd
import zipfile
from io import BytesIO
from ..fetch_data import fetch_data
from xml.sax.saxutils import escape
from fastapi.responses import Response, StreamingResponse

CHUNK_SIZE = 1000


# ─────────────────────────────────────────────
# CONFIGURATION / CONSTANTS
# ─────────────────────────────────────────────
MAX_DIRECTORS = 10
MAX_SIGNATORIES = 8

REPORT_HEADER = {
    "rentity_id": "43",
    "rentity_branch": "43",
    "submission_code": "E",
    "report_code": "CTR",
    "entity_reference": "UBL-CTR-11MAY2026-11MAY2026-1-1",
    "submission_date": "2026-05-13T00:00:00",
    "currency_code_local": "PKR",
}

REPORTING_PERSON = {
    "gender": "M",
    "title": "Divisional Head",
    "first_name": "Farrukh",
    "last_name": "Khalil",
    "birthdate": "1984-06-30T00:00:00",
    "ssn": "4220127380591",
    "nationality1": "PK",
    "tph_contact_type": "PAOFF",
    "tph_communication_type": "COLAN",
    "tph_country_prefix": "92",
    "tph_number": "990332957",
    "tph_extension": "17110",
    "address_type": "PAOFF",
    "address": "UBL Head Office",
    "town": "Karachi",
    "city": "Karachi",
    "country_code": "PK",
    "state": "Sindh",
    "email": "farrukh.khalil@ubl.com.pk",
    "occupation": "Money Laundering AND Reporting Officer",
}

LOCATION = {
    "address_type": "PAOFF",
    "address": "UBL Head Office",
    "city": "karachi",
    "country_code": "PK",
    "state": "Sindh",
}


# ─────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────
def safe(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s in ("?", "nan", "NaN", "None", ""):
        return ""
    return escape(s)


def is_available(val):
    if val is None:
        return False
    s = str(val).strip()
    return s not in ("?", "nan", "NaN", "None", "")


def format_date(val):
    s = str(val).strip()
    if "T" in s:
        return s
    try:
        dt = pd.to_datetime(s)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return s


def format_exchange_rate(val):
    try:
        return str(round(float(val), 3))
    except (ValueError, TypeError):
        return safe(val)


def tag(name, value):
    #print(f"processing tag: {name}, value: {value}, type: {type(value)}")

    if value is None:
        #print(f"None value detected, tag is {name} , value is {value}")
        return f"<{name}>{' '}</{name}>\n"
    if isinstance(value, float) and str(value) == 'nan':
       #print(f"NaN value detected, tag is {name} , value is {value}")
        return f"<{name}>{' '}</{name}>\n"
    if value == "":
        #print(f"Empty string detected, tag is {name} , value is {value}")
        return f"<{name}>{' '}</{name}>\n"

    
    return f"<{name}>{safe(value)}</{name}>\n"


def country_prefix_to_code(val):
    s = str(val).strip()
    if s.upper() == "PK":
        return 92
    if s in ("?", "nan", "NaN", "None", ""):
        return ""
    return s


# ─────────────────────────────────────────────
# XML BLOCK BUILDERS (shared)
# ─────────────────────────────────────────────
def build_report_header(transaction_date):
    dt = pd.to_datetime(transaction_date)           
    formatted_date = dt.strftime("%d%b%Y").upper()
    today_date = pd.to_datetime("today").strftime("%Y-%m-%d")
    print("Today's date:", today_date)
    # h = REPORT_HEADER
    REPORT_HEADER = {
    "rentity_id": "43",
    "rentity_branch": "43",
    "submission_code": "E",
    "report_code": "CTR",
    "entity_reference": f"UBL-CTR-{formatted_date}-{formatted_date}-1-1",
    "submission_date": today_date+'T00:00:00',
    "currency_code_local": "PKR",
    }

    xml = "<report>\n"
    for k in ("rentity_id", "rentity_branch", "submission_code", "report_code",
              "entity_reference", "submission_date", "currency_code_local"):
        xml += tag(k, REPORT_HEADER[k])
        # print(f"xml inside build report header is {xml}")
    return xml


def build_reporting_person():
    rp = REPORTING_PERSON
    xml = "<reporting_person>\n"
    xml += tag("gender", rp["gender"])
    xml += tag("title", rp["title"])
    xml += tag("first_name", rp["first_name"])
    xml += tag("last_name", rp["last_name"])
    xml += tag("birthdate", rp["birthdate"])

    xml += tag("ssn", rp["ssn"])
    xml += tag("nationality1", rp["nationality1"])
    xml += "<phones>\n<phone>\n"
    xml += tag("tph_contact_type", rp["tph_contact_type"])
    xml += tag("tph_communication_type", rp["tph_communication_type"])
    xml += tag("tph_country_prefix", rp["tph_country_prefix"])
    xml += tag("tph_number", rp["tph_number"])
    xml += tag("tph_extension", rp["tph_extension"])
    xml += "</phone>\n</phones>\n"
    xml += "<addresses>\n<address>\n"
    xml += tag("address_type", rp["address_type"])
    xml += tag("address", rp["address"])
    xml += tag("town", rp["town"])
    xml += tag("city", rp["city"])
    xml += tag("country_code", rp["country_code"])
    xml += tag("state", rp["state"])
    xml += "</address>\n</addresses>\n"
    xml += tag("email", rp["email"])
    xml += tag("occupation", rp["occupation"])
    xml += "</reporting_person>\n"
    return xml


def build_location():
    loc = LOCATION
    xml = "<location>\n"
    xml += tag("address_type", loc["address_type"])
    xml += tag("address", loc["address"])
    xml += tag("city", loc["city"])
    xml += tag("country_code", loc["country_code"])
    xml += tag("state", loc["state"])
    xml += "</location>\n<reason></reason>\n"
    return xml


def build_phone_block(contact_type, comm_type, prefix, number):
    tph_country_prefix = country_prefix_to_code(prefix)
    if tph_country_prefix is not None and str(tph_country_prefix) != 'NaN' and str(tph_country_prefix) != 'nan':
        try:
            tph_country_prefix = int(float(tph_country_prefix))
        except (ValueError,TypeError):
            pass



    if number is not None and str(number) != 'NaN' and str(number) != 'nan':
        try:
            number = int(float(number))
        except (ValueError,TypeError):
            pass
    # if tph_country_prefix == "92.0":
    #     tph_country_prefix = 92
    # if number is not None:
    #     number = int(number)
    
    xml = "<phones>\n<phone>\n"
    xml += tag("tph_contact_type", contact_type)
    xml += tag("tph_communication_type", comm_type)
    xml += tag("tph_country_prefix", tph_country_prefix)
    xml += tag("tph_number", number)
    xml += "</phone>\n</phones>\n"
    return xml


def build_address_block(addr_type, address, city, country_code, state):
    xml = "<addresses>\n<address>\n"
    xml += tag("address_type", addr_type)
    xml += tag("address", address)
    xml += tag("city", city)
    xml += tag("country_code", country_code)
    xml += tag("state", state)
    xml += "</address>\n</addresses>\n"
    return xml


def build_foreign_currency_block(direction, currency_code, amount, rate):
    xml = f"<{direction}_foreign_currency>\n"
    xml += tag("foreign_currency_code", currency_code)
    xml += tag("foreign_amount", amount)
    xml += tag("foreign_exchange_rate", format_exchange_rate(rate))
    xml += f"</{direction}_foreign_currency>\n"
    return xml


def build_transaction_header(row):
    xml = "<transaction>\n"
    xml += tag("transactionnumber", row.get("transactionnumber", ""))
    xml += tag("transaction_location", row.get("transaction_location", ""))
    xml += tag("transaction_description", row.get("transaction_description", ""))
    xml += tag("date_transaction", format_date(row.get("date_transaction", "")))
    xml += tag("teller", row.get("teller", ""))
    xml += tag("authorized", row.get("authorized", ""))
    xml += tag("transmode_code", row.get("transmode_code", ""))
    xml += tag("amount_local", row.get("amount_local", ""))
    return xml


# ─────────────────────────────────────────────
# PERSON BLOCK (used for the non-account party)
# ─────────────────────────────────────────────
def build_person_block(tag_name, row, prefix, include_residence=True,
                       include_comments=False):
    """
    Build from_person / to_person.
    prefix: 'TFMC_' or 'TTMC_' — the person-side column prefix.
    include_residence: True for entity cases, False for individual cases.
    include_comments: True for individual cases (<comments></comments>).
    """

    xml = f"<{tag_name}>\n"
    
    xml += tag("gender", row.get(f"{prefix}Gender", ""))
    xml += tag("title", row.get(f"{prefix}Title", ""))
    xml += tag("first_name", row.get(f"{prefix}First_Name", ""))
    xml += tag("last_name", row.get(f"{prefix}Last_Name", ""))
    xml += tag("birthdate", format_date(row.get(f"{prefix}Birth_Date", "")))
    xml += tag("mothers_name", row.get(f"{prefix}Mother_Name", ""))
    if row.get(f"{prefix}ssn_type", "") == "PPT":
        xml += tag("passport_number", row.get(f"{prefix}ssn", ""))
        xml += tag("passport_country", row.get(f"{prefix}nationality1", ""))
    else:
        ssn = (row.get(f"{prefix}ssn", ""))
        if ssn != "":
            if isinstance(ssn, str):
                ssn = int(float(ssn))

        xml += tag("ssn", ssn)
    xml += tag("nationality1", row.get(f"{prefix}nationality1", ""))
    if include_residence:
        xml += tag("residence", row.get(f"{prefix}Residence", ""))
    xml += build_phone_block(
        row.get(f"{prefix}tph_contact_type", ""),
        row.get(f"{prefix}tph_communication_type", ""),
        row.get(f"{prefix}tph_country_prefix", ""),
        row.get(f"{prefix}tph_number", ""),
    )

    xml += build_address_block(
        row.get(f"{prefix}address_type", ""),
        row.get(f"{prefix}address", ""),
        row.get(f"{prefix}city", ""),
        row.get(f"{prefix}country_code", ""),
        row.get(f"{prefix}state", ""),
    )
    xml += tag("occupation", row.get(f"{prefix}occupation", ""))
    if include_comments:
        xml += "<comments></comments>\n"
    xml += f"</{tag_name}>\n"
    return xml


# ─────────────────────────────────────────────
# DIRECTOR BLOCK (entity cases only)
# ─────────────────────────────────────────────
def build_director_block(row, dir_num, entity_city, entity_country, entity_state):
    prefix = f"DIR{dir_num}_"
    if not is_available(row.get(f"{prefix}FIRSTNAME", "")):
        return ""
    xml = f"<Director>\n"
    xml += tag("gender", row.get(f"{prefix}GNDR", ""))
    xml += tag("title", row.get(f"{prefix}TITL", ""))
    xml += tag("first_name", row.get(f"{prefix}FIRSTNAME", ""))
    xml += tag("last_name", row.get(f"{prefix}LASTNAME", ""))
    xml += tag("birthdate", format_date(row.get(f"{prefix}DATE_OF_BIRTH", "")))
    xml += tag("fathers_name", row.get(f"{prefix}FATHER_NAME", ""))
    if row.get(f"{prefix}SSN_TYPE", "") == "PPT":
        xml += tag("passport_number", row.get(f"{prefix}SSN", ""))
        xml += tag("passport_country", row.get(f"{prefix}nationality1", ""))
    else:
        ssn = row.get(f"{prefix}SSN", "")
        if ssn != "nan" :
            if isinstance(ssn, str):
                ssn = int(float(ssn))

        xml += tag("ssn", ssn)
    xml += tag("nationality1", row.get(f"{prefix}nationality1", ""))
    xml += tag("residence", row.get(f"{prefix}Residence", ""))
    xml += build_phone_block(
        row.get(f"{prefix}tph_contact_type", ""),
        row.get(f"{prefix}tph_communication_type", ""),
        row.get(f"{prefix}tph_country_prefix", ""),
        row.get(f"{prefix}TPH_NUMBER", ""),
    )
    xml += build_address_block(row.get(f"{prefix}address_type"), row.get(f"{prefix}ADDRESS", ""),
                               row.get(f"{prefix}CITY"), entity_country,  row.get(f"{prefix}STATE"))
    xml += tag("occupation", row.get(f"{prefix}OCCUPATION", ""))
    xml += tag("role", "ERDIR")

    xml += f"</Director>\n"
    return xml


# ─────────────────────────────────────────────
# SIGNATORY BLOCK
# Two variants: entity vs individual
# ─────────────────────────────────────────────
def build_signatory_entity(row, sig_num, entity_city, entity_country, entity_state,
                           is_primary=False):
    """Signatory for entity cases: hardcoded PAPVT/COMOB/PARPE, nationality=PK."""
    prefix = f"SIGNATORY{sig_num}_"
    if not is_available(row.get(f"{prefix}FIRSTNAME", "")):
        return ""
    xml = f"<Signatory>\n"

    if is_primary:
        xml += tag("is_primary", row.get(f"{prefix}IS_PRIMARY", ""))
    xml += "<t_person>\n"
    xml += tag("gender", row.get(f"{prefix}GNDR", ""))
    xml += tag("title", row.get(f"{prefix}TITL", ""))
    xml += tag("first_name", row.get(f"{prefix}FIRSTNAME", ""))
    xml += tag("last_name", row.get(f"{prefix}LASTNAME", ""))
    xml += tag("birthdate", format_date(row.get(f"{prefix}DATE_OF_BIRTH", "")))
    xml += tag("fathers_name", row.get(f"{prefix}FATHER_NAME", ""))
    if row.get(f"{prefix}SSN_TYPE", "") == "PPT":
        xml += tag("passport_number", row.get(f"{prefix}SSN", ""))
        xml += tag("passport_country", row.get(f"{prefix}nationality1", ""))
    else:
        ssn = (row.get(f"{prefix}SSN", ""))
        if ssn != "":
            if isinstance(ssn, str):
                ssn = int(float(ssn))
        xml += tag("ssn", ssn)

    xml += tag("nationality1", row.get(f"{prefix}nationality1", ""))
    xml += tag("residence", row.get(f"{prefix}Residence", ""))
    xml += build_phone_block(
        row.get(f"{prefix}tph_contact_type", ""),
        row.get(f"{prefix}tph_communication_type", ""),
        row.get(f"{prefix}tph_country_prefix", ""),
        row.get(f"{prefix}TPH_NUMBER", ""),
    )
    xml += build_address_block(row.get(f"{prefix}address_type"), row.get(f"{prefix}ADDRESS", ""),
                               row.get(f"{prefix}CITY"), entity_country, row.get(f"{prefix}STATE"))
    xml += tag("occupation", row.get(f"{prefix}OCCUPATION", ""))
    xml += "</t_person>\n"
    xml += tag("role", "ARPYS")
    xml += f"</Signatory>\n"

    return xml


def build_signatory_individual(row, sig_num, acct_city, acct_country, acct_state,
                               is_primary=False):
    """Signatory for individual cases: PAREG/COMOB/PAREG, no residence."""
    prefix = f"SIGNATORY{sig_num}_"
    if not is_available(row.get(f"{prefix}FIRSTNAME", "")):
        return ""
    xml = f"<Signatory>\n"
    if is_primary:
        xml += tag("is_primary", row.get(f"{prefix}IS_PRIMARY", ""))
    xml += "<t_person>\n"
    xml += tag("gender", row.get(f"{prefix}GNDR", ""))
    xml += tag("title", row.get(f"{prefix}TITL", ""))
    xml += tag("first_name", row.get(f"{prefix}FIRSTNAME", ""))
    xml += tag("last_name", row.get(f"{prefix}LASTNAME", ""))
    xml += tag("birthdate", format_date(row.get(f"{prefix}DATE_OF_BIRTH", "")))
    xml += tag("fathers_name", row.get(f"{prefix}FATHER_NAME", ""))
    if row.get(f"{prefix}SSN_TYPE", "") == "PPT":
        xml += tag("passport_number", row.get(f"{prefix}SSN", ""))
        xml += tag("passport_country", row.get(f"{prefix}nationality1", ""))
    else:
        ssn = (row.get(f"{prefix}SSN", ""))
        if ssn != "":
            if isinstance(ssn, str):
                ssn = int(float(ssn))

        xml += tag("ssn", ssn)

    xml += tag("nationality1", row.get(f"{prefix}nationality1", ""))
    xml += build_phone_block(
        row.get(f"{prefix}tph_contact_type", ""),
        row.get(f"{prefix}tph_communication_type", ""),
        row.get(f"{prefix}tph_country_prefix", ""),
        row.get(f"{prefix}TPH_NUMBER", ""),
    )
    xml += build_address_block(row.get(f"{prefix}address_type"), row.get(f"{prefix}ADDRESS", ""),
                               row.get(f"{prefix}CITY"),  row.get(f"{prefix}country_code"), row.get(f"{prefix}STATE"))
    xml += tag("occupation", row.get(f"{prefix}OCCUPATION", ""))
    xml += "</t_person>\n"
    xml += tag("role", "ARPYS")
    xml += f"</Signatory>\n"
    return xml


# ─────────────────────────────────────────────
# ACCOUNT BLOCKS
# ─────────────────────────────────────────────
def build_entity_account_block(row, prefix, direction):
    """
    Full account block for ENTITY cases: account + t_entity + directors + signatories.
    prefix: 'TFMC_' or 'TTMC_'
    direction: 'from' or 'to'
    """
    entity_city = safe(row.get(f"{prefix}city", ""))
    entity_country = safe(row.get(f"{prefix}country_code", ""))
    entity_state = safe(row.get(f"{prefix}state", ""))

    xml = f"<{direction}_account>\n"
    xml += tag("institution_name", row.get(f"{prefix}institution_name", ""))
    xml += tag("institution_code", row.get(f"{prefix}institution_code", ""))
    xml += tag("non_bank_institution", row.get(f"{prefix}non_bank_institution", ""))
    xml += tag("branch", row.get(f"{prefix}branch", ""))
    xml += tag("account", row.get(f"{prefix}account", ""))
    xml += tag("currency_code", row.get(f"{prefix}currency_code", ""))
    xml += tag("account_name", row.get(f"{prefix}account_name", ""))
    xml += tag("personal_account_type", row.get(f"{prefix}personal_account_type", ""))

    # t_entity
    xml += "<t_entity>\n"
    xml += tag("name", row.get(f"{prefix}name", ""))
    xml += tag("incorporation_legal_form", row.get(f"{prefix}incorporation_legal_form", ""))
    xml += tag("business", row.get(f"{prefix}business", ""))
    xml += build_phone_block(
        row.get(f"{prefix}tph_contact_type", ""),
        row.get(f"{prefix}tph_communication_type", ""),
        row.get(f"{prefix}tph_country_prefix", ""),
        row.get(f"{prefix}tph_number", ""),
    )
    xml += build_address_block(
        row.get(f"{prefix}address_type", ""),
        row.get(f"{prefix}address", ""),
        entity_city, entity_country, entity_state,
    )
    xml += tag("incorporation_country_code", row.get(f"{prefix}incorporation_country_code", ""))

    for i in range(1, MAX_DIRECTORS + 1):
        xml += build_director_block(row, i, entity_city, entity_country, entity_state)

    tax_num = ""
    if is_available(row.get("TMC_TAX_NUM", "")):
        tax_num = row["TMC_TAX_NUM"]
        tax_num = int(float(tax_num))
    elif is_available(row.get(f"{prefix}TAX_NUM", "")):
        tax_num = row[f"{prefix}TAX_NUM"]
        tax_num = int(float(tax_num))

    xml += tag("tax_number", tax_num)
    xml += "</t_entity>\n"

    for i in range(1, MAX_SIGNATORIES + 1):
        xml += build_signatory_entity(row, i, entity_city, entity_country, entity_state,
                                      is_primary=(i == i))

    xml += tag("opened", format_date(row.get(f"{prefix}open", "")))
    xml += tag("status_code", row.get(f"{prefix}status_code", ""))
    xml += f"</{direction}_account>\n"
    return xml


def build_individual_account_block(row, prefix, direction):
    """
    Account block for INDIVIDUAL cases: account + signatories (no t_entity, no directors).
    prefix: 'TFMC_' or 'TTMC_'
    direction: 'from' or 'to'
    """
    acct_city = safe(row.get(f"{prefix}city", ""))
    acct_country = safe(row.get(f"{prefix}country_code", ""))
    acct_state = safe(row.get(f"{prefix}state", ""))

    xml = f"<{direction}_account>\n"
    xml += tag("institution_name", row.get(f"{prefix}institution_name", ""))
    xml += tag("institution_code", row.get(f"{prefix}institution_code", ""))
    xml += tag("non_bank_institution", row.get(f"{prefix}non_bank_institution", ""))
    xml += tag("branch", row.get(f"{prefix}branch", ""))
    xml += tag("account", row.get(f"{prefix}account", ""))
    xml += tag("currency_code", row.get(f"{prefix}currency_code", ""))
    xml += tag("account_name", row.get(f"{prefix}account_name", ""))
    xml += tag("personal_account_type", row.get(f"{prefix}personal_account_type", ""))

    for i in range(1, MAX_SIGNATORIES + 1):
        xml += build_signatory_individual(row, i, acct_city, acct_country, acct_state,
                                          is_primary=(i == 1))

    xml += tag("opened", format_date(row.get(f"{prefix}open", "")))
    xml += tag("status_code", row.get(f"{prefix}status_code", ""))
    xml += f"</{direction}_account>\n"
    return xml


# ─────────────────────────────────────────────
# TRANSACTION BUILDERS
# ─────────────────────────────────────────────
def build_transaction_entity_deposit(row):
    """Entity Deposit: t_from (person) + t_to_my_client (entity account)."""
    xml = build_transaction_header(row)

    xml += "<t_from>\n"
    xml += tag("from_funds_code", row.get("TFMC_from_funds_code", ""))
    currency = safe(row.get("TTMC_currency_code", "PKR"))
    fc = row.get("TTMC_Foreign_Currency_Code", "")
    if currency != "PKR" and is_available(fc):
        foreign_amount = row.get("TTMC_Foreign_Amount", "")
        foreign_exchange_rate = row.get("TTMC_Foreign_Exchange_Rate", "")

        if foreign_amount is not None and str(foreign_amount) != 'nan' and str(foreign_amount) != 'NaN':
            foreign_amount = int(float(foreign_amount))
        if foreign_exchange_rate is not None and str(foreign_exchange_rate) != 'nan' and str(foreign_exchange_rate) != 'NaN':
            foreign_exchange_rate = round(float(foreign_exchange_rate), 2)
        xml += build_foreign_currency_block("from", fc,
                   foreign_amount,
                   foreign_exchange_rate)
    xml += build_person_block("from_person", row, "TFMC_")
    xml += tag("from_country", row.get("TFMC_from_country", ""))
    xml += "</t_from>\n"

    xml += "<t_to_my_client>\n"
    xml += tag("to_funds_code", row.get("TTMC_to_funds_code", ""))
    xml += build_entity_account_block(row, "TTMC_", "to")
    xml += tag("to_country", row.get("TTMC_to_country", ""))
    xml += "</t_to_my_client>\n"

    xml += "</transaction>\n"
    return xml


def build_transaction_entity_withdrawal(row):
    """Entity Withdrawal: t_from_my_client (entity account) + t_to (person)."""
    xml = build_transaction_header(row)

    xml += "<t_from_my_client>\n"
    xml += tag("from_funds_code", row.get("TFMC_from_funds_code", ""))
    xml += build_entity_account_block(row, "TFMC_", "from")
    xml += tag("from_country", row.get("TFMC_from_country", ""))
    xml += "</t_from_my_client>\n"

    xml += "<t_to>\n"
    xml += tag("to_funds_code", row.get("TTMC_to_funds_code", ""))
    currency = safe(row.get("TFMC_currency_code", "PKR"))
    if currency != "PKR":
        fc = row.get("TFMC_Foreign_Currency_Code", "")
        
        if is_available(fc):
            foreign_amount = row.get("TFMC_Foreign_Amount", "")
            foreign_exchange_rate =  row.get("TFMC_Foreign_Exchange_Rate", "")
            if foreign_amount is not None and str(foreign_amount) != 'nan' and str(foreign_amount) != 'NaN':
                foreign_amount = int(float(foreign_amount))
            if foreign_exchange_rate is not None and str(foreign_exchange_rate) != 'nan' and str(foreign_exchange_rate) != 'NaN':
                foreign_exchange_rate = foreign_exchange_rate
            xml += build_foreign_currency_block("to", fc,
                       foreign_amount,
                       foreign_exchange_rate)
    xml += build_person_block("to_person", row, "TTMC_")
    xml += tag("to_country", row.get("TTMC_to_country", ""))
    xml += "</t_to>\n"

    xml += "</transaction>\n"
    return xml


def build_transaction_individual_deposit(row):
    """Individual Deposit: t_from_my_client (person) + t_to_my_client (individual account)."""
    xml = build_transaction_header(row)

    xml += "<t_from_my_client>\n"
    xml += tag("from_funds_code", row.get("TFMC_from_funds_code", ""))
    currency = safe(row.get("TTMC_currency_code", "PKR"))
    fc = row.get("TTMC_Foreign_Currency_Code", "")
    if currency != "PKR" and is_available(fc):
        foreign_amount = row.get("TTMC_Foreign_Amount", "")
        foreign_exchange_rate = row.get("TTMC_Foreign_Exchange_Rate", "")
        
        if foreign_amount is not None and str(foreign_amount) != 'nan' and str(foreign_amount) != 'NaN':
            foreign_amount = int(float(foreign_amount))
         
        if foreign_exchange_rate is not None and str(foreign_exchange_rate) != 'nan' and str(foreign_exchange_rate) != 'NaN':
            foreign_exchange_rate = round(float(foreign_exchange_rate),2)
        xml += build_foreign_currency_block("from", fc,
                   foreign_amount,
                   foreign_exchange_rate)
    xml += build_person_block("from_person", row, "TFMC_",
                              include_residence=False, include_comments=True)
    xml += tag("from_country", row.get("TFMC_from_country", ""))
    xml += "</t_from_my_client>\n"

    xml += "<t_to_my_client>\n"
    xml += tag("to_funds_code", row.get("TTMC_to_funds_code", ""))
    xml += build_individual_account_block(row, "TTMC_", "to")
    xml += tag("to_country", row.get("TTMC_to_country", ""))
    xml += "</t_to_my_client>\n"

    xml += "<comments></comments>\n"
    xml += "</transaction>\n"
    return xml


def build_transaction_individual_withdrawal(row):
    """Individual Withdrawal: t_from_my_client (individual account) + t_to_my_client (person)."""
    xml = build_transaction_header(row)

    xml += "<t_from_my_client>\n"
    xml += tag("from_funds_code", row.get("TFMC_from_funds_code", ""))
    xml += build_individual_account_block(row, "TFMC_", "from")
    xml += tag("from_country", row.get("TFMC_from_country", ""))
    xml += "</t_from_my_client>\n"

    xml += "<t_to_my_client>\n"
    xml += tag("to_funds_code", row.get("TTMC_to_funds_code", ""))
    currency = safe(row.get("TFMC_currency_code", "PKR"))
    if currency != "PKR":
        fc = row.get("TFMC_Foreign_Currency_Code", "")
        if is_available(fc):
            foreign_amount = row.get("TFMC_Foreign_Amount", "")
            foreign_exchange_rate = row.get("TFMC_Foreign_Exchange_Rate", "")
            if foreign_amount is not None and str(foreign_amount) != 'nan' and str(foreign_amount) != 'NaN':
                foreign_amount = int(float(foreign_amount))
            if foreign_exchange_rate is not None and str(foreign_exchange_rate) != 'nan' and str(foreign_exchange_rate) != 'NaN':
                foreign_amount = round(float(foreign_exchange_rate),2)

            xml += build_foreign_currency_block("to", fc,
                       foreign_amount,
                       foreign_exchange_rate)
    xml += build_person_block("to_person", row, "TTMC_",
                              include_residence=False, include_comments=True)
    xml += tag("to_country", row.get("TTMC_to_country", ""))
    xml += "</t_to_my_client>\n"

    xml += "<comments></comments>\n"
    xml += "</transaction>\n"
    return xml


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
BUILDERS = {
    "entity_deposit": build_transaction_entity_deposit,
    "entity_withdrawal": build_transaction_entity_withdrawal,
    "individual_deposit": build_transaction_individual_deposit,
    "individual_withdrawal": build_transaction_individual_withdrawal,
}

def create_file_name(transaction_date, cr_dr_flag, entity_individual_flag, split_num):
    if cr_dr_flag == 'CR' :
        part_1 = 'DEP'
    elif cr_dr_flag == 'DR' :
        part_1 = 'WHT'
    if entity_individual_flag == 'ENTITY' :
        part_2 = 'ENT'
    elif entity_individual_flag == 'INDIVIDUAL' :
        part_2 = 'IND'

    file_name = f"{part_1} {part_2} {split_num} {transaction_date}.xml"
    return file_name

def generate_ctr_csv(transaction_date, cr_dr_flag, entity_individual_flag):
    case = None
    if cr_dr_flag == 'DR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_deposit'
    elif cr_dr_flag == 'DR' and entity_individual_flag == 'ENTITY':
        case = 'entity_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'ENTITY':
        case = 'entity_deposit'
    elif entity_individual_flag == 'individual' and cr_dr_flag == 'debit':
        case = 'individual_withdrawal'
    
    df = fetch_data(transaction_date, cr_dr_flag, entity_individual_flag)
    print(f"DF AFTER NULL IN CHECK QUERY {df} , length of the df is {len(df)}")
    if len(df.columns) == 1:
         return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
    elif df.empty:
        return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
    print(f"df has been created: {df.head}")
    df = df.fillna("")
    # for i in range(1,9):
    #     df[f'SIGNATORY{i}']
    # df['']
    print(f"df length is {len(df)}")
    file_name = f"CTR_{transaction_date}_{cr_dr_flag}_{entity_individual_flag}.csv"

    logger.info(f"Generating CSV FILE: {file_name}")
    logger.info(f"DataFrame Shape: {df.shape}")
    logger.info(f"Number of Records: {len(df)}")

    output_dir = r"C:\Regalytics\CTR\ctr_backend\generated_csv"

    os.makedirs(output_dir, exist_ok = True)

    
 
    csv_buffer = BytesIO()
    csv = df.to_csv(csv_buffer, index = False)
    csv_buffer.seek(0)
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    saved_file_path = os.path.join(output_dir, f"{file_name.replace('.csv','')}_{timestamp}.csv")

    with open(saved_file_path, "wb") as f:
        f.write(csv_buffer.getvalue())

    logger.info(f"CSV saved to disk at: {saved_file_path}")

    logger.info(f"Returning CSV FILE : {file_name}")
    logger.info(f"CSV SIZE : {csv_buffer.getbuffer().nbytes} bytes")

    return Response(
        content = csv_buffer.getvalue(),
         media_type = "text/csv",
        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }

    )



async def generate_ctr_xml(file : UploadFile = File(...),
    # # transaction_date: str = ''
    data : str = Form(...)):

    contents = await file.read()


    print(f"file read successfully")
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16', 'utf-8-sig']
    df = None
    used_encoding = None
    # print(contents)
    parsed_data = CTRData(**json.loads(data))
    transaction_date = parsed_data.transaction_date
    cr_dr_flag = parsed_data.cr_dr_flag
    entity_individual_flag = parsed_data.entity_individual_flag
    print(f"parsed data is ", parsed_data)
    for enc in encodings:
        try:
            csv_string = contents.decode(enc)
            csv_io = io.StringIO(csv_string)
            df = pd.read_csv(csv_io, low_memory = False)
            used_encoding = enc
            print(f"successfully decoded with {enc} encoding")
            break
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            print(f"Encoding {enc} failed : {str(e)}")
            continue
        except Exception as e:
            print(f"Error with {enc} failed : {str(e)}")
            continue
    if df is None:
        csv_string = contents.decode('latin-1')
        csv_io = io.StringIO(csv_string)
        df = pd.read_csv(csv_io, low_memory = False)
        used_encoding = 'latin-1 (fallback)'
        print(f" used fallback: latin-1")
        
    print(f"Rows : {len(df)} , columns : {df.columns}")
    


    case = None
    if cr_dr_flag == 'DR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_deposit'
    elif cr_dr_flag == 'DR' and entity_individual_flag == 'ENTITY':
        case = 'entity_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'ENTITY':
        case = 'entity_deposit'
    elif entity_individual_flag == 'individual' and cr_dr_flag == 'debit':
        case = 'individual_withdrawal'



    if len(df.columns) == 1:
         return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
    elif df.empty:
        return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
        
    print(f"csv has been created and saved as output_file.csv")
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:

        for split_num, start in enumerate(range(0, len(df), CHUNK_SIZE), start=1):

            chunk_df = df.iloc[start:start + CHUNK_SIZE]

            xml = build_report_header(transaction_date)
            xml += build_reporting_person()
            xml += build_location()

            build_transaction = BUILDERS[case]

            for _, row in chunk_df.iterrows():
                xml += build_transaction(row)

            xml += "</report>"

            file_name = create_file_name(
                transaction_date,
                cr_dr_flag,
                entity_individual_flag,
                split_num
            )
            
            zip_file.writestr(file_name, xml)

    # print(f"xml final is {xml}")

    
    output_dir = r"C:\Regalytics\CTR\ctr_backend\generated_xml_ahmed"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    os.makedirs(output_dir, exist_ok = True)

    zip_buffer.seek(0)
    saved_file_path = os.path.join(output_dir, f"{file_name}_{timestamp}.xml")
    with open(saved_file_path, "wb") as f:
        f.write(zip_buffer.getvalue())
    
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition":
                f'attachment; filename="CTR_{cr_dr_flag}_{entity_individual_flag}_{transaction_date}.zip"'
        }
    )

def generate_ctr_xml_backup(transaction_date, cr_dr_flag, entity_individual_flag, df):
    case = None
    if cr_dr_flag == 'DR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'INDIVIDUAL':
        case = 'individual_deposit'
    elif cr_dr_flag == 'DR' and entity_individual_flag == 'ENTITY':
        case = 'entity_withdrawal'
    elif cr_dr_flag == 'CR' and entity_individual_flag == 'ENTITY':
        case = 'entity_deposit'
    elif entity_individual_flag == 'individual' and cr_dr_flag == 'debit':
        case = 'individual_withdrawal'

    
    if len(df.columns) == 1:
         return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
    elif df.empty:
        return Response(
            content = "No data found for the given criteria",
            status_code = 404,
            media_type = "text/plain"
        )
        
    print(f"csv has been created and saved as output_file.csv")
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:

        for split_num, start in enumerate(range(0, len(df), CHUNK_SIZE), start=1):

            chunk_df = df.iloc[start:start + CHUNK_SIZE]

            xml = build_report_header(transaction_date)
            xml += build_reporting_person()
            xml += build_location()

            build_transaction = BUILDERS[case]

            for _, row in chunk_df.iterrows():
                xml += build_transaction(row)

            xml += "</report>"

            file_name = create_file_name(
                transaction_date,
                cr_dr_flag,
                entity_individual_flag,
                split_num
            )

            zip_file.writestr(file_name, xml)

    

    zip_buffer.seek(0)

    # before returning, save the zip file to disk for testing
    with open(f"CTR_{transaction_date}.zip", "wb") as f:
        f.write(zip_buffer.getvalue())

    

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition":
                f'attachment; filename="CTR_{cr_dr_flag}_{entity_individual_flag}_{transaction_date}.zip"'
        }
    )

if __name__ == "__main__":
    case = 'entity_deposit'  # Change this to the desired case: 'entity_deposit', 'entity_withdrawal', 'individual_deposit', 'individual_withdrawal'
    excel_file = r'C:\Regalytics\CTR\Queries\Sample Data Files\ENTITY_DEPOSIT(CREDIT)_CASH_TRXNS(11-MAY-2026).xlsx'

    output_file = r'C:\Regalytics\CTR\Queries\Generated XL\entity_deposit.csv'


    generate_ctr_xml('2026-05-11', 'CR', 'ENTITY')