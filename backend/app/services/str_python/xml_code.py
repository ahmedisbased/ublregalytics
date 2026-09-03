"""
STR/goAML XML Generator v2

Simple rules:
  - Check each account (TFMC or TTMC): entity? -> entity schema. individual? -> individual schema.
  - Entity detection uses TFMC_customer_Type_code / TTMC_customer_Type_code from transaction data.
  - Once entity is detected, actual account info is populated from the Entity Query DataFrame
    (which has MAIN_CLIENT, DIRECTOR_CLIENT, MANDATE_CLIENT rows with richer data).
    Falls back to transaction row data if entity query has no matching account.
  - Entity schema: has t_entity block (with director(s) + mandate holders), NO institution_country/account_category/is_primary/title
  - Individual schema: has institution_country, account_category, is_primary, title. NO t_entity.
  - Linked accounts: attached where primary account is. Each checked entity/individual separately.
  - Entity linked accounts from ENTITY.txt, individual linked accounts from CBS_CC+WALLET.
"""

import pandas as pd
from lxml import etree
import copy, os
import logging
from typing import Any
# from .fetch_data import fetch_data
from .fetch_data_working import fetch_data
from .errors import NoRecordsFound, StrGenerationError, StrProcessingError, StrTeradataError
from .observability import add_str_log, exception_text, mask_account


logger = logging.getLogger(__name__)

ENTITY_CODES = ['3', '03','31','32','33','34','35','36','37','38']

def safe(val):
    if pd.isna(val): return ''
    s = str(val).strip()
    return '' if s in ('?', '-') else s

def is_entity(code):
    return safe(code) in ENTITY_CODES

def add(parent, tag, text=None):
    el = etree.SubElement(parent, tag)
    if text is not None: el.text = str(text)
    return el

def clean_amount(val):
    s = safe(val)
    if not s: return s
    s = s.replace(',','').replace('\r','').replace('\n','').strip()
    if '.' in s:
        try:
            f = float(s)
            s = str(int(f)) if f == int(f) else f"{f:.2f}".rstrip('0').rstrip('.')
        except ValueError: pass
    return s

def clean_biz(val, fallback=''):
    s = safe(val).rstrip('_ ').strip()
    return s if s else safe(fallback)

def parse_date(val):
    s = safe(val)
    if not s or 'T' in s: return s
    try:
        from datetime import datetime
        return datetime.strptime(s, '%m/%d/%Y').strftime('%Y-%m-%dT00:00:00')
    except: return s

# ============ BUILDING BLOCKS ============

def build_phones(parent, ct, comm, prefix, number):
    num = safe(number)
    if not num: return
    phones = add(parent, 'phones')
    phone = add(phones, 'phone')
    add(phone, 'tph_contact_type', safe(ct) or 'PAPVT')
    add(phone, 'tph_communication_type', safe(comm) or 'COMOB')
    add(phone, 'tph_country_prefix', safe(prefix) or '92')
    add(phone, 'tph_number', num)

def build_address(parent, atype, addr_val, city, country, state):
    a = safe(addr_val)
    if len(a) > 99:
        a = a[:99]
    if not a: return
    addresses = add(parent, 'addresses')
    address = add(addresses, 'address')
    add(address, 'address_type', safe(atype) or 'PAPVT')
    add(address, 'address', a)
    add(address, 'city', safe(city))
    add(address, 'country_code', safe(country) or 'PK')
    add(address, 'state', safe(state))

def build_t_entity(parent, name, inc_form, business, ph_ct, ph_comm, ph_pfx, ph_num, a_type, addr_val, city, country, state, erp_data=None):
    te = add(parent, 't_entity')
    add(te, 'name', safe(name))
    add(te, 'incorporation_legal_form', safe(inc_form) or 'ETPVT')
    add(te, 'business', safe(business))
    build_phones(te, ph_ct, ph_comm, ph_pfx, ph_num)
    build_address(te, a_type, addr_val, city, country, state)
    if erp_data and safe(erp_data.get('first_name','')):
        rp = add(te, 'related_persons')
        erp = add(rp, 'entity_related_person')
        person = add(erp, 'person')
        if safe(erp_data.get('gender','')): add(person, 'gender', safe(erp_data['gender']))
        add(person, 'first_name', safe(erp_data.get('first_name','')))
        add(person, 'last_name', safe(erp_data.get('last_name','')))
        add(person, 'birthdate', safe(erp_data.get('birthdate','')))
        add(person, 'mothers_name', safe(erp_data.get('mothers_name','')))
        add(person, 'ssn', safe(erp_data.get('ssn','')))
        add(person, 'nationality1', safe(erp_data.get('nationality1','')))
        build_phones(person, erp_data.get('ph_ct',''), erp_data.get('ph_comm',''), erp_data.get('ph_pfx',''), erp_data.get('ph_num',''))
        build_address(person, erp_data.get('a_type',''), erp_data.get('addr',''), erp_data.get('city',''), erp_data.get('country',''), erp_data.get('state',''))
        add(person, 'occupation', safe(erp_data.get('occupation','')))
        add(erp, 'role', safe(erp_data.get('role','ERPRO')))
    return te

def build_related_persons(parent, gender, first_name, last_name, birthdate, mothers_name, ssn, nationality1, ph_ct, ph_comm, ph_pfx, ph_num, a_type, addr_val, city, country, state, occupation, role='ARCTA', with_is_primary=False, title=None):
    rp = add(parent, 'related_persons')
    arp = add(rp, 'account_related_person')
    if with_is_primary: add(arp, 'is_primary', 'true')
    tp = add(arp, 't_person')
    add(tp, 'gender', safe(gender))
    if title and safe(title): add(tp, 'title', safe(title))
    add(tp, 'first_name', safe(first_name))
    add(tp, 'last_name', safe(last_name))
    add(tp, 'birthdate', safe(birthdate))
    add(tp, 'mothers_name', safe(mothers_name))
    add(tp, 'ssn', safe(ssn))
    add(tp, 'nationality1', safe(nationality1))
    build_phones(tp, ph_ct, ph_comm, ph_pfx, ph_num)
    build_address(tp, a_type, addr_val, city, country, state)
    add(tp, 'occupation', safe(occupation))
    add(arp, 'role', safe(role) or 'ARCTA')
    return rp

# ============ ACCOUNT BUILDERS ============

def build_entity_account(parent_tag, parent, row, pfx, related_accounts_xml=None, erp_role='ERPRO'):
    wrapper = add(parent, parent_tag)
    fc_tag = 'from_funds_code' if 'from' in parent_tag else 'to_funds_code'
    add(wrapper, fc_tag, safe(row.get(fc_tag, '')))
    tag = 'from_account' if 'from' in parent_tag else 'to_account'
    acct = add(wrapper, tag)
    add(acct, 'institution_name', safe(row.get(f'{pfx}institution_name', 'UNITED BANK LIMITED')))
    add(acct, 'swift', safe(row.get(f'{pfx}swift', 'UNILPKKA')))
    add(acct, 'branch', safe(row.get(f'{pfx}branch', '')))
    add(acct, 'account', safe(row.get(f'{pfx}account_', '')))

    add(acct, 'iban', safe(row.get(f'{pfx}iban', '')))
    

    add(acct, 'currency_code', safe(row.get(f'{pfx}currency_code', 'PKR')))
    add(acct, 'account_name', safe(row.get(f'{pfx}account_name', '')))
    add(acct, 'account_type', safe(row.get(f'{pfx}account_type', '')))
    biz = clean_biz(row.get(f'{pfx}Occupation', ''))
    erp_data = {'first_name': row.get(f'{pfx}first_name',''), 'last_name': row.get(f'{pfx}last_name',''), 'birthdate': row.get(f'{pfx}birthdate',''), 'mothers_name': row.get(f'{pfx}mothers_name',''), 'ssn': row.get(f'{pfx}ssn',''), 'nationality1': row.get(f'{pfx}nationality1',''), 'ph_ct': row.get(f'{pfx}tph_contact_type',''), 'ph_comm': row.get(f'{pfx}tph_communication_type',''), 'ph_pfx': row.get(f'{pfx}tph_country_prefix',''), 'ph_num': row.get(f'{pfx}tph_number',''), 'a_type': row.get(f'{pfx}addtyp',''), 'addr': row.get(f'{pfx}address',''), 'city': row.get(f'{pfx}city',''), 'country': row.get(f'{pfx}country_code',''), 'state': row.get(f'{pfx}state',''), 'occupation': biz, 'role': erp_role}
    build_t_entity(acct, row.get(f'{pfx}account_name',''), 'ETSOL', biz, row.get(f'{pfx}tph_contact_type','PAPVT'), row.get(f'{pfx}tph_communication_type','COMOB'), row.get(f'{pfx}tph_country_prefix','92'), row.get(f'{pfx}tph_number',''), row.get(f'{pfx}addtyp','PAPVT'), row.get(f'{pfx}address',''), row.get(f'{pfx}city',''), row.get(f'{pfx}country_code','PK'), row.get(f'{pfx}state',''), erp_data=erp_data)
    build_related_persons(acct, gender=row.get(f'{pfx}gender',''), first_name=row.get(f'{pfx}first_name',''), last_name=row.get(f'{pfx}last_name',''), birthdate=row.get(f'{pfx}birthdate',''), mothers_name=row.get(f'{pfx}mothers_name',''), ssn=row.get(f'{pfx}ssn',''), nationality1=row.get(f'{pfx}nationality1',''), ph_ct=row.get(f'{pfx}tph_contact_type',''), ph_comm=row.get(f'{pfx}tph_communication_type',''), ph_pfx=row.get(f'{pfx}tph_country_prefix',''), ph_num=row.get(f'{pfx}tph_number',''), a_type=row.get(f'{pfx}addtyp',''), addr_val=row.get(f'{pfx}address',''), city=row.get(f'{pfx}city',''), country=row.get(f'{pfx}country_code',''), state=row.get(f'{pfx}state',''), occupation=biz, role=safe(row.get(f'{pfx}role','ARCTA')))
    if related_accounts_xml is not None: acct.append(related_accounts_xml)
    add(acct, 'opened', safe(row.get(f'{pfx}opened', '')))
    add(acct, 'status_code', safe(row.get(f'{pfx}STATUS_CODE', '')))
    add(acct, 'beneficiary_comment', safe(row.get(f'{pfx}beneficiary_comment', '')))
    add(acct, 'comments', safe(row.get(f'{pfx}comments', '')))
    c_tag = 'from_country' if 'from' in parent_tag else 'to_country'
    add(wrapper, c_tag, safe(row.get(f'{pfx}to_country', 'PK')))
    return wrapper

def build_individual_account(parent_tag, parent, row, pfx, related_accounts_xml=None, is_primary_acct=False):
    wrapper = add(parent, parent_tag)
    fc_tag = 'from_funds_code' if 'from' in parent_tag else 'to_funds_code'
    add(wrapper, fc_tag, safe(row.get(fc_tag, '')))
    tag = 'from_account' if 'from' in parent_tag else 'to_account'
    acct = add(wrapper, tag)
    add(acct, 'institution_name', safe(row.get(f'{pfx}institution_name', 'UNITED BANK LIMITED')))
    add(acct, 'swift', safe(row.get(f'{pfx}swift', 'UNILPKKA')))
    add(acct, 'institution_country', safe(row.get(f'{pfx}institution_country', 'PK')))
    add(acct, 'branch', safe(row.get(f'{pfx}branch', '')))
    add(acct, 'account_category', 'ACMPA')
    add(acct, 'account', safe(row.get(f'{pfx}account_', '')))
    logger.debug("Building individual account block with prefix %s", pfx)
    add(acct, 'iban', safe(row.get(f'{pfx}iban', '')))
    
    add(acct, 'currency_code', safe(row.get(f'{pfx}currency_code', 'PKR')))
    add(acct, 'account_name', safe(row.get(f'{pfx}account_name', '')))
    add(acct, 'account_type', safe(row.get(f'{pfx}account_type', '')))
    build_related_persons(acct, gender=row.get(f'{pfx}gender',''), first_name=row.get(f'{pfx}first_name',''), last_name=row.get(f'{pfx}last_name',''), birthdate=row.get(f'{pfx}birthdate',''), mothers_name=row.get(f'{pfx}mothers_name',''), ssn=row.get(f'{pfx}ssn',''), nationality1=row.get(f'{pfx}nationality1',''), ph_ct=row.get(f'{pfx}tph_contact_type',''), ph_comm=row.get(f'{pfx}tph_communication_type',''), ph_pfx=row.get(f'{pfx}tph_country_prefix',''), ph_num=row.get(f'{pfx}tph_number',''), a_type=row.get(f'{pfx}addtyp',''), addr_val=row.get(f'{pfx}address',''), city=row.get(f'{pfx}city',''), country=row.get(f'{pfx}country_code',''), state=row.get(f'{pfx}state',''), occupation=row.get(f'{pfx}Occupation',''), role=safe(row.get(f'{pfx}role','ARCTA')), with_is_primary=True, title=safe(row.get(f'{pfx}title','Mr.')))
    if related_accounts_xml is not None: acct.append(related_accounts_xml)
    add(acct, 'opened', safe(row.get(f'{pfx}opened', '')))
    if is_primary_acct: add(acct, 'balance', '')
    add(acct, 'status_code', safe(row.get(f'{pfx}STATUS_CODE', '')))
    add(acct, 'beneficiary_comment', clean_amount(row.get(f'{pfx}_beneficiary_comment', '')))
    add(acct, 'comments', clean_amount(row.get(f'{pfx}comments', '')))
    c_tag = 'from_country' if 'from' in parent_tag else 'to_country'
    add(wrapper, c_tag, safe(row.get(f'{pfx}to_country', 'PK')))
    return wrapper

def build_entity_account_from_query(parent_tag, parent, entity_rows, txn_row, related_accounts_xml=None):
    """
    Build entity account using data from the Entity Query DataFrame.
    Called when transaction determines entity, but actual account info
    comes from entity query (which has MAIN_CLIENT, DIRECTOR_CLIENT, MANDATE_CLIENT rows).
    txn_row is still used for funds_code only.
    """
    wrapper = add(parent, parent_tag)
    fc_tag = 'from_funds_code' if 'from' in parent_tag else 'to_funds_code'
    add(wrapper, fc_tag, safe(txn_row.get(fc_tag, '')))
    tag = 'from_account' if 'from' in parent_tag else 'to_account'
    acct = add(wrapper, tag)

    # Use MAIN_CLIENT row for primary account-level info; fall back to first row
    main_rows = entity_rows[entity_rows['TYP'] == 'MAIN_CLIENT']
    primary = main_rows.iloc[0] if len(main_rows) > 0 else entity_rows.iloc[0]

    add(acct, 'institution_name', safe(primary.get('institution_name', 'UNITED BANK LIMITED')))
    add(acct, 'swift', safe(primary.get('swift', 'UNILPKKA')))
    add(acct, 'branch', safe(primary.get('branch', '')))
    add(acct, 'account', safe(primary.get('account_', '')))
    add(acct, 'iban', safe(primary.get('IBAN_NUM', '')))
    add(acct, 'currency_code', safe(primary.get('currency_code', 'PKR')))
    add(acct, 'account_name', safe(primary.get('account_name', '')))
    add(acct, 'account_type', safe(primary.get('account_type', '')))

    biz = clean_biz(primary.get('business', ''), primary.get('CUST_TYPE_DESC', ''))

    # --- Build t_entity with director(s) as entity_related_person(s) ---
    te = add(acct, 't_entity')
    add(te, 'name', safe(primary.get('ENTITY_NAME', primary.get('account_name', ''))))
    add(te, 'incorporation_legal_form', safe(primary.get('incorporation_legal_form', 'ETPVT')))
    add(te, 'business', safe(biz))
    build_phones(te, primary.get('tph_contact_type', 'PAPVT'), primary.get('tph_communication_type', 'COMOB'),
                 primary.get('tph_country_prefix', '92'), primary.get('tph_number', ''))
    build_address(te, primary.get('address_type', 'PAPVT'), primary.get('address', ''),
                  primary.get('city', ''), primary.get('country_code', 'PK'), primary.get('state', ''))

    # Add director(s) as entity_related_person inside t_entity
    director_rows = entity_rows[entity_rows['TYP'] == 'DIRECTOR_CLIENT']
    if len(director_rows) > 0:
        rp_ent = add(te, 'related_persons')
        for _, d_row in director_rows.iterrows():
            erp = add(rp_ent, 'entity_related_person')
            person = add(erp, 'person')
            if safe(d_row.get('gender', '')): add(person, 'gender', safe(d_row['gender']))
            add(person, 'first_name', safe(d_row.get('first_name', '')))
            add(person, 'last_name', safe(d_row.get('last_name', '')))
            add(person, 'birthdate', safe(d_row.get('birthdate', '')))
            add(person, 'mothers_name', safe(d_row.get('mothers_name', '')))
            add(person, 'ssn', safe(d_row.get('ssn', '')))
            add(person, 'nationality1', safe(d_row.get('nationality1', '')))
            build_phones(person, d_row.get('tph_contact_type', ''), d_row.get('tph_communication_type', ''),
                         d_row.get('tph_country_prefix', ''), d_row.get('tph_number', ''))
            build_address(person, d_row.get('address_type', ''), d_row.get('address', ''),
                          d_row.get('city', ''), d_row.get('country_code', ''), d_row.get('state', ''))
            add(person, 'occupation', safe(biz))
            add(erp, 'role', 'ERDIR')
    elif safe(primary.get('first_name', '')):
        # No directors found, use main client as entity_related_person
        rp_ent = add(te, 'related_persons')
        erp = add(rp_ent, 'entity_related_person')
        person = add(erp, 'person')
        if safe(primary.get('gender', '')): add(person, 'gender', safe(primary['gender']))
        add(person, 'first_name', safe(primary.get('first_name', '')))
        add(person, 'last_name', safe(primary.get('last_name', '')))
        add(person, 'birthdate', safe(primary.get('birthdate', '')))
        add(person, 'mothers_name', safe(primary.get('mothers_name', '')))
        add(person, 'ssn', safe(primary.get('ssn', '')))
        add(person, 'nationality1', safe(primary.get('nationality1', '')))
        build_phones(person, primary.get('tph_contact_type', ''), primary.get('tph_communication_type', ''),
                     primary.get('tph_country_prefix', ''), primary.get('tph_number', ''))
        build_address(person, primary.get('address_type', ''), primary.get('address', ''),
                      primary.get('city', ''), primary.get('country_code', ''), primary.get('state', ''))
        add(person, 'occupation', safe(biz))
        add(erp, 'role', 'ERPRO')

    # --- Build account related_persons from MAIN_CLIENT ---
    build_related_persons(acct, gender=primary.get('gender', ''), first_name=primary.get('first_name', ''),
                          last_name=primary.get('last_name', ''), birthdate=primary.get('birthdate', ''),
                          mothers_name=primary.get('mothers_name', ''), ssn=primary.get('ssn', ''),
                          nationality1=primary.get('nationality1', ''),
                          ph_ct=primary.get('tph_contact_type', ''), ph_comm=primary.get('tph_communication_type', ''),
                          ph_pfx=primary.get('tph_country_prefix', ''), ph_num=primary.get('tph_number', ''),
                          a_type=primary.get('address_type', ''), addr_val=primary.get('address', ''),
                          city=primary.get('city', ''), country=primary.get('country_code', ''),
                          state=primary.get('state', ''), occupation=biz,
                          role=safe(primary.get('Role_', 'ARCTA')))

    # --- Add MANDATE_CLIENT holders as additional related_persons ---
    mandate_rows = entity_rows[entity_rows['TYP'] == 'MANDATE_CLIENT']
    for _, m_row in mandate_rows.iterrows():
        build_related_persons(acct, gender=m_row.get('gender', ''), first_name=m_row.get('first_name', ''),
                              last_name=m_row.get('last_name', ''), birthdate=m_row.get('birthdate', ''),
                              mothers_name=m_row.get('mothers_name', ''), ssn=m_row.get('ssn', ''),
                              nationality1=m_row.get('nationality1', ''),
                              ph_ct=m_row.get('tph_contact_type', ''), ph_comm=m_row.get('tph_communication_type', ''),
                              ph_pfx=m_row.get('tph_country_prefix', ''), ph_num=m_row.get('tph_number', ''),
                              a_type=m_row.get('address_type', ''), addr_val=m_row.get('address', ''),
                              city=m_row.get('city', ''), country=m_row.get('country_code', ''),
                              state=m_row.get('state', ''), occupation=biz,
                              role=safe(m_row.get('ROLE_OUTER', 'ARPYS')))

    if related_accounts_xml is not None:
        acct.append(related_accounts_xml)

    add(acct, 'opened', safe(primary.get('opened', '')))
    add(acct, 'status_code', safe(primary.get('STATUS_CODE', '')))
    bc = clean_amount(primary.get('beneficiary_comment', ''))
    cm = clean_amount(primary.get('comments', ''))
    if bc: add(acct, 'beneficiary_comment', bc)
    if cm: add(acct, 'comments', cm)

    c_tag = 'from_country' if 'from' in parent_tag else 'to_country'
    add(wrapper, c_tag, safe(primary.get('to_country', 'PK')))
    return wrapper

# ============ RELATED ACCOUNT BUILDERS ============

def build_entity_related_account(row):
    ara = etree.SubElement(etree.Element('d'), 'account_related_account')
    logger.debug("Building entity-related account block")
    add(ara, 'account_account_relation', 'AARLO')
    acct = add(ara, 'account')
    add(acct, 'institution_name', safe(row.get('institution_name', 'UNITED BANK LIMITED')))
    add(acct, 'swift', safe(row.get('swift', 'UNILPKKA')))
    add(acct, 'branch', safe(row.get('branch', '')))
    add(acct, 'account', safe(row.get('ACCT_NUM', row.get('account_', ''))))
    add(acct, 'iban', safe(row.get('ACCT_NUM', row.get('iban', ''))))
    add(acct, 'currency_code', safe(row.get('currency_code', 'PKR')))
    add(acct, 'account_name', safe(row.get('account_name', '')))
    biz = clean_biz(row.get('business', ''), row.get('CUST_TYPE_DESC', ''))
    erp_data = {'gender': row.get('gender',''), 'first_name': row.get('first_name',''), 'last_name': row.get('last_name',''), 'birthdate': row.get('birthdate',''), 'mothers_name': row.get('mothers_name',''), 'ssn': row.get('ssn',''), 'nationality1': row.get('nationality1',''), 'ph_ct': row.get('tph_contact_type',''), 'ph_comm': row.get('tph_communication_type',''), 'ph_pfx': row.get('tph_country_prefix',''), 'ph_num': row.get('tph_number',''), 'a_type': row.get('address_type',''), 'addr': row.get('address',''), 'city': row.get('city',''), 'country': row.get('country_code',''), 'state': row.get('state',''), 'occupation': biz, 'role': 'ERDIR'}
    build_t_entity(acct, name=row.get('ENTITY_NAME', row.get('account_name','')), inc_form=row.get('incorporation_legal_form','ETPVT'), business=biz, ph_ct=row.get('tph_contact_type','PAPVT'), ph_comm=row.get('tph_communication_type','COMOB'), ph_pfx=row.get('tph_country_prefix','92'), ph_num=row.get('tph_number',''), a_type=row.get('address_type','PAPVT'), addr_val=row.get('address',''), city=row.get('city',''), country=row.get('country_code','PK'), state=row.get('state',''), erp_data=erp_data)
    build_related_persons(acct, gender=row.get('gender',''), first_name=row.get('first_name',''), last_name=row.get('last_name',''), birthdate=row.get('birthdate',''), mothers_name=row.get('mothers_name',''), ssn=row.get('ssn',''), nationality1=row.get('nationality1',''), ph_ct=row.get('tph_contact_type',''), ph_comm=row.get('tph_communication_type',''), ph_pfx=row.get('tph_country_prefix',''), ph_num=row.get('tph_number',''), a_type=row.get('address_type',''), addr_val=row.get('address',''), city=row.get('city',''), country=row.get('country_code',''), state=row.get('state',''), occupation=biz, role=row.get('Role_','ARCTA'))
    add(acct, 'opened', safe(row.get('opened', '')))
    close_dt = safe(row.get('ACCT_CLOSE_DATE', ''))
    status = safe(row.get('STATUS_CODE', ''))
    if status == 'ASCBC' and close_dt: add(acct, 'closed', parse_date(close_dt))
    add(acct, 'status_code', status)
    bc = clean_amount(row.get('DEBIT_AMT', row.get('beneficiary_comment', '')))
    cm = clean_amount(row.get('CREDIT_AMT', row.get('comments', '')))
    if bc: add(acct, 'beneficiary_comment', bc)
    if cm: add(acct, 'comments', cm)
    return ara

def build_individual_related_account(row, src='cbs'):
    ara = etree.SubElement(etree.Element('d'), 'account_related_account')
    add(ara, 'account_account_relation', 'AARLO')
    acct = add(ara, 'account')
    if src == 'cbs':
        add(acct, 'institution_name', safe(row.get('institution_name','UNITED BANK LIMITED')))
        add(acct, 'swift', safe(row.get('swift','UNILPKKA')))
        add(acct, 'branch', safe(row.get('BRANCH','')))
        add(acct, 'account', safe(row.get('ACCT_NO','')))
        add(acct, 'currency_code', safe(row.get('CCY','PKR')))
        add(acct, 'account_name', safe(row.get('ACCT_TITLE','')))
        add(acct, 'comments', safe(row.get('comments','')))
        add(acct, 'beneficiary_comment', safe(row.get('beneficiary_comment','')))


 

        occ = safe(row.get('occupation', row.get('CUSTOMER_TYPE_DESC','')))
        role = safe(row.get('ROLE','ARCTA'))
    else:
        add(acct, 'institution_name', safe(row.get('institution_name','UNITED BANK LIMITED')))
        add(acct, 'swift', safe(row.get('swift','UNILPKKA')))
        add(acct, 'branch', safe(row.get('branch','')))
        add(acct, 'account', safe(row.get('ACCT_NUM','')))
        add(acct, 'currency_code', safe(row.get('currency_code','PKR')))
        add(acct, 'account_name', safe(row.get('account_name','')))
        occ = clean_biz(row.get('business',''), row.get('CUST_TYPE_DESC',''))
        role = safe(row.get('Role_','ARCTA'))
    build_related_persons(acct, gender=row.get('gender',''), first_name=row.get('first_name',''), last_name=row.get('last_name',''), birthdate=row.get('birthdate',''), mothers_name=row.get('mothers_name',''), ssn=row.get('ssn',''), nationality1=row.get('nationality1',''), ph_ct=row.get('tph_contact_type',''), ph_comm=row.get('tph_communication_type',''), ph_pfx=row.get('tph_country_prefix',''), ph_num=row.get('tph_number',''), a_type=row.get('address_type',''), addr_val=row.get('address',''), city=row.get('city',''), country=row.get('country_code',''), state=row.get('state',''), occupation=occ, role=role)
    if src == 'cbs':
        add(acct, 'opened', parse_date(row.get('ACCT_OPEN_DATE','')))
        close_dt = safe(row.get('ACCT_CLOSE_DATE',''))
        if close_dt and close_dt != '-': add(acct, 'closed', parse_date(close_dt))
        add(acct, 'status_code', safe(row.get('STATUS_CODE','')))
        bc = clean_amount(row.get('DEBIT_AMT',''))
        cm = clean_amount(row.get('CREDIT_AMT',''))
        if bc: add(acct, 'beneficiary_comment', bc)
        if cm: add(acct, 'comments', cm)
    else:
        add(acct, 'opened', safe(row.get('opened','')))
        status = safe(row.get('STATUS_CODE',''))
        if status == 'ASCBC':
            close = safe(row.get('ACCT_CLOSE_DATE',''))
            if close: add(acct, 'closed', parse_date(close))
        add(acct, 'status_code', status)
    return ara

def build_entity_related_account_from_cbs(row):
    ara = etree.SubElement(etree.Element('d'), 'account_related_account')
    add(ara, 'account_account_relation', 'AARLO')
    acct = add(ara, 'account')
    add(acct, 'institution_name', safe(row.get('institution_name','UNITED BANK LIMITED')))
    add(acct, 'swift', safe(row.get('swift','UNILPKKA')))
    add(acct, 'branch', safe(row.get('BRANCH','')))
    add(acct, 'account', safe(row.get('ACCT_NO','')))
    add(acct, 'currency_code', safe(row.get('CCY','PKR')))
    add(acct, 'account_name', safe(row.get('ACCT_TITLE','')))
    biz = safe(row.get('CUSTOMER_TYPE_DESC',''))
    erp_data = {'gender': row.get('gender',''), 'first_name': row.get('first_name',''), 'last_name': row.get('last_name',''), 'birthdate': row.get('birthdate',''), 'mothers_name': row.get('mothers_name',''), 'ssn': row.get('ssn',''), 'nationality1': row.get('nationality1',''), 'ph_ct': row.get('tph_contact_type',''), 'ph_comm': row.get('tph_communication_type',''), 'ph_pfx': row.get('tph_country_prefix',''), 'ph_num': row.get('tph_number',''), 'a_type': row.get('address_type',''), 'addr': row.get('address',''), 'city': row.get('city',''), 'country': row.get('country_code',''), 'state': row.get('state',''), 'occupation': row.get('occupation', biz), 'role': 'ERDIR'}
    build_t_entity(acct, row.get('ACCT_TITLE',''), 'ETPVT', biz, row.get('tph_contact_type','PAPVT'), row.get('tph_communication_type','COMOB'), row.get('tph_country_prefix','92'), row.get('tph_number',''), row.get('address_type','PAPVT'), row.get('address',''), row.get('city',''), row.get('country_code','PK'), row.get('state',''), erp_data=erp_data)
    build_related_persons(acct, gender=row.get('gender',''), first_name=row.get('first_name',''), last_name=row.get('last_name',''), birthdate=row.get('birthdate',''), mothers_name=row.get('mothers_name',''), ssn=row.get('ssn',''), nationality1=row.get('nationality1',''), ph_ct=row.get('tph_contact_type',''), ph_comm=row.get('tph_communication_type',''), ph_pfx=row.get('tph_country_prefix',''), ph_num=row.get('tph_number',''), a_type=row.get('address_type',''), addr_val=row.get('address',''), city=row.get('city',''), country=row.get('country_code',''), state=row.get('state',''), occupation=row.get('occupation', biz), role=row.get('ROLE','ARCTA'))
    add(acct, 'opened', parse_date(row.get('ACCT_OPEN_DATE','')))
    close_dt = safe(row.get('ACCT_CLOSE_DATE',''))
    if close_dt and close_dt != '-': add(acct, 'closed', parse_date(close_dt))
    add(acct, 'status_code', safe(row.get('STATUS_CODE','')))
    bc = clean_amount(row.get('DEBIT_AMT',''))
    cm = clean_amount(row.get('CREDIT_AMT',''))
    if bc: add(acct, 'beneficiary_comment', bc)
    if cm: add(acct, 'comments', cm)
    return ara

# ============ DATA LOADING ============


def load_data(p_acct_no, p_trxn_no, p_date_from, p_date_to, logs=None):
    """Load all 5 data files"""
    request_logs = logs if logs is not None else []
    add_str_log(
        request_logs,
        logger,
        "INFO",
        "data_loading",
        "Loading the five STR datasets required for XML generation.",
        {"account": mask_account(p_acct_no)},
    )
    # CBS_CC
    trxns, wallet, cbs, entity, entity_detail = fetch_data(
        p_acct_no,
        p_trxn_no,
        p_date_from,
        p_date_to,
        logs=request_logs,
    )
    # cbs = pd.read_csv(CBS_CC_FILE, sep='\t', dtype=str, keep_default_na=False)
    cbs.columns = [c.strip() for c in cbs.columns]

    # WALLET
    # wallet = pd.read_csv(WALLET_FILE, sep='\t', dtype=str, keep_default_na=False)
    wallet.columns = [c.strip() for c in wallet.columns]

    # Merge CBS_CC + WALLET vertically, drop duplicates
    if len(wallet) > 0 and len(wallet.columns) > 1:
        # Align columns
        common_cols = list(set(cbs.columns) & set(wallet.columns))
        ind_linked = pd.concat([cbs[common_cols], wallet[common_cols]], ignore_index=True)
    else:
        ind_linked = cbs.copy()

    ind_linked = ind_linked.drop_duplicates()

    # ENTITY
    # entity = pd.read_csv(ENTITY_FILE, sep='\t', dtype=str, keep_default_na=False)
    
    entity.columns = [c.strip() for c in entity.columns]

    # TRANSACTIONS - handle duplicate column names
    # trxns = pd.read_csv(TRXNS_FILE, sep='\t', dtype=str, keep_default_na=False,
    #                     header=0)
    # Fix duplicate column names - pandas appends .1 to duplicates

    rename_map = {
        'TFMC_customer_Type_code.1': 'TTMC_customer_Type_code',
        'TFMC_customer_Type_desc.1': 'TTMC_customer_Type_desc',
    }

    trxns.rename(columns=rename_map, inplace=True)

    trxns.columns = [c.strip() for c in trxns.columns]

    # Entity detail (MAIN_CLIENT, DIRECTOR_CLIENT, MANDATE_CLIENT) for TFMC/TTMC entity population
    entity_detail.columns = [c.strip() for c in entity_detail.columns]

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "data_loading",
        "STR datasets normalized for XML generation.",
        {
            "transactions": len(trxns),
            "individual_linked_rows": len(ind_linked),
            "entity_rows": len(entity),
            "entity_detail_rows": len(entity_detail),
        },
    )
    return ind_linked, entity, trxns, entity_detail

def build_related_accounts(main_account, ind_linked_df, entity_df):
    ra = etree.Element('related_accounts')
    seen = set()
    main_str = str(main_account).strip()
    for _, row in entity_df.iterrows():
        acct_num = safe(row.get('ACCT_NUM', row.get('account_', '')))
        if acct_num == main_str or acct_num in seen: continue
        seen.add(acct_num)
        if is_entity(safe(row.get('CUST_TYPE_CD', ''))):
            ra.append(build_entity_related_account(row))
        else:
            ra.append(build_individual_related_account(row, src='entity'))
    acct_col = 'ACCT_NO' if 'ACCT_NO' in ind_linked_df.columns else 'ACCT_NUM'
    for _, row in ind_linked_df.iterrows():
        acct_num = safe(row.get(acct_col, ''))
        if acct_num == main_str or acct_num in seen: continue
        seen.add(acct_num)
        if is_entity(safe(row.get('CUSTOMER_TYPE_CODE', row.get('CUST_TYPE_CD', '')))):
            ra.append(build_entity_related_account_from_cbs(row))
        else:
            ra.append(build_individual_related_account(row, src='cbs'))
    return ra if len(ra) > 0 else None

# ============ MAIN GENERATOR ============

def generate_xml(
    main_account,
    transaction_number=None,
    from_date=None,
    to_date=None,
    logs: list[dict[str, Any]] | None = None,
):
    request_logs = logs if logs is not None else []
    account_label = mask_account(main_account)
    add_str_log(
        request_logs,
        logger,
        "INFO",
        "xml_generation",
        "STR XML generation started.",
        {"account": account_label, "transaction_filter": bool(transaction_number)},
    )

    try:
        ind_linked, entity, trxns, entity_detail = load_data(
            main_account,
            transaction_number,
            from_date,
            to_date,
            logs=request_logs,
        )
    except StrGenerationError:
        raise
    except Exception as error:
        add_str_log(
            request_logs,
            logger,
            "ERROR",
            "data_loading",
            "Unexpected failure while loading STR data.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrProcessingError("data_loading", error) from error

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "xml_generation",
        "STR data loading completed; building XML document.",
        {"transactions": len(trxns)},
    )

    try:
        main_str = str(main_account).strip()
        ra_block = build_related_accounts(main_account, ind_linked, entity)
        related_account_count = len(ra_block) if ra_block is not None else 0
        add_str_log(
            request_logs,
            logger,
            "INFO",
            "related_accounts",
            "Related account section prepared.",
            {"related_accounts": related_account_count},
        )

        report = etree.Element('report')
        transaction_count = len(trxns)
        add_str_log(
            request_logs,
            logger,
            "INFO",
            "transaction_build",
            "Building transaction XML blocks.",
            {"transaction_count": transaction_count},
        )
        for transaction_index, (_, row) in enumerate(trxns.iterrows(), start=1):
            if transaction_index <= 10:
                add_str_log(
                    request_logs,
                    logger,
                    "INFO",
                    "transaction_build",
                    "Building transaction block.",
                    {"transaction_number_present": bool(safe(row.get('transactionnumber', '')))},
                )
            elif transaction_index == 11:
                add_str_log(
                    request_logs,
                    logger,
                    "INFO",
                    "transaction_build",
                    "Additional transaction-level logs omitted to keep the UI readable.",
                    {"omitted_transactions": transaction_count - 10},
                )

            txn = add(report, 'transaction')
            add(txn, 'transactionnumber', safe(row['transactionnumber']))
            add(txn, 'date_transaction', safe(row['date_transaction']))
            add(txn, 'authorized', safe(row['authorized']))
            add(txn, 'transmode_code', safe(row['transmode_code']))
            add(txn, 'amount_local', clean_amount(row['amount_local']))
            tfmc_acct = safe(row.get('TFMC_account_', ''))
            ttmc_acct = safe(row.get('TTMC_account_', ''))
            # Related accounts go where the primary account is
            tfmc_ra = copy.deepcopy(ra_block) if (tfmc_acct == main_str and ra_block is not None) else None
            ttmc_ra = copy.deepcopy(ra_block) if (ttmc_acct == main_str and ra_block is not None) else None
            # TFMC - check type from transaction, build schema accordingly
            if is_entity(row.get('TFMC_customer_Type_code', '')):
                # Entity detected from transaction -> use Entity Detail data if available
                ent_col = 'ACCT_NUM' if 'ACCT_NUM' in entity_detail.columns else 'account_'
                ent_rows = entity_detail[entity_detail[ent_col].astype(str).str.strip() == tfmc_acct] if len(entity_detail) > 0 else pd.DataFrame()
                if len(ent_rows) > 0:
                    build_entity_account_from_query('t_from_my_client', txn, ent_rows, row, related_accounts_xml=tfmc_ra)
                else:
                    build_entity_account('t_from_my_client', txn, row, 'TFMC_', related_accounts_xml=tfmc_ra)
            else:
                build_individual_account('t_from_my_client', txn, row, 'TFMC_', related_accounts_xml=tfmc_ra, is_primary_acct=(tfmc_acct == main_str))
            # TTMC - check type from transaction, build schema accordingly
            if is_entity(row.get('TTMC_customer_Type_code', '')):
                # Entity detected from transaction -> use Entity Detail data if available
                ent_col = 'ACCT_NUM' if 'ACCT_NUM' in entity_detail.columns else 'account_'
                ent_rows = entity_detail[entity_detail[ent_col].astype(str).str.strip() == ttmc_acct] if len(entity_detail) > 0 else pd.DataFrame()
                if len(ent_rows) > 0:
                    build_entity_account_from_query('t_to_my_client', txn, ent_rows, row, related_accounts_xml=ttmc_ra)
                else:
                    build_entity_account('t_to_my_client', txn, row, 'TTMC_', related_accounts_xml=ttmc_ra)
            else:
                build_individual_account('t_to_my_client', txn, row, 'TTMC_', related_accounts_xml=ttmc_ra, is_primary_acct=(ttmc_acct == main_str))
        xml_string = etree.tostring(report, encoding='unicode')
    except (NoRecordsFound, StrTeradataError, StrProcessingError):
        raise
    except Exception as error:
        add_str_log(
            request_logs,
            logger,
            "ERROR",
            "xml_build",
            "XML document construction failed after data loading.",
            {"error_type": error.__class__.__name__, "error": exception_text(error)},
        )
        raise StrProcessingError(
            "xml_build",
            error,
            category="XML_GENERATION",
            code="XML_GENERATION_ERROR",
        ) from error

    add_str_log(
        request_logs,
        logger,
        "INFO",
        "xml_generation",
        "STR XML generated successfully.",
        {"transactions": transaction_count, "xml_characters": len(xml_string)},
    )
    return xml_string

if __name__ == '__main__':
    main_account = '326247471'
    print("Loading data and generating XML...")
    report = generate_xml(main_account)
    xml_str = etree.tostring(report, encoding='unicode', pretty_print=False)
    with open('/home/claude/output.xml', 'w', encoding='utf-8') as f: f.write(xml_str)
    print(f"XML generated. Size: {len(xml_str)} chars")
    root = etree.fromstring(xml_str.encode())
    txns = root.findall('transaction')
    print(f"Transactions: {len(txns)}")
    for i, t in enumerate(txns[:5]):
        fa = t.find('.//from_account'); ta = t.find('.//to_account')
        fa_te = fa.find('t_entity') is not None; ta_te = ta.find('t_entity') is not None
        fa_erp = fa.find('.//entity_related_person') is not None; ta_erp = ta.find('.//entity_related_person') is not None
        fa_ic = fa.find('institution_country') is not None; ta_ic = ta.find('institution_country') is not None
        fa_ip = fa.find('.//is_primary') is not None; ta_ip = ta.find('.//is_primary') is not None
        fa_ra = fa.find('related_accounts'); fa_ra_n = len(list(fa_ra)) if fa_ra is not None else 0
        ta_ra = ta.find('related_accounts'); ta_ra_n = len(list(ta_ra)) if ta_ra is not None else 0
        print(f"  Txn {i+1}: TFMC={fa.find('account').text} [{'ENT' if fa_te else 'IND'}] ERP={fa_erp} ic={fa_ic} ip={fa_ip} RA={fa_ra_n} | TTMC={ta.find('account').text} [{'ENT' if ta_te else 'IND'}] ERP={ta_erp} ic={ta_ic} ip={ta_ip} RA={ta_ra_n}")
