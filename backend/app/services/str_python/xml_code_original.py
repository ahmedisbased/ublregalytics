"""
STR/goAML XML Generator v2

Simple rules:
  - Check each account (TFMC or TTMC): entity? -> entity schema. individual? -> individual schema.
  - Entity schema: has t_entity block (with director info), NO institution_country/account_category/is_primary/title
  - Individual schema: has institution_country, account_category, is_primary, title. NO t_entity.
  - Linked accounts: attached where primary account is. Each checked entity/individual separately.
  - Entity linked accounts from ENTITY.txt, individual linked accounts from CBS_CC+WALLET.
"""

import pandas as pd
from lxml import etree
import copy, os
from .fetch_data import fetch_data

ENTITY_CODES = ['3', '03','31','32','33','34','35','36','37','38']
DATA_DIR = '/mnt/user-data/uploads'

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
    print(f"INSIDE BUILD ENTITY ACCOUNT AND THE PREFIX IS {pfx}")

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
    print(f"INSIDE BUILD INDIVIDUAL ACCOUNT AND THE PREFIX IS {pfx}")
    add(acct, 'iban', safe(row.get(f'{pfx}iban', '')))

    add(acct, 'currency_code', safe(row.get(f'{pfx}currency_code', 'PKR')))
    add(acct, 'account_name', safe(row.get(f'{pfx}account_name', '')))
    add(acct, 'account_type', safe(row.get(f'{pfx}account_type', '')))
    build_related_persons(acct, gender=row.get(f'{pfx}gender',''), first_name=row.get(f'{pfx}first_name',''), last_name=row.get(f'{pfx}last_name',''), birthdate=row.get(f'{pfx}birthdate',''), mothers_name=row.get(f'{pfx}mothers_name',''), ssn=row.get(f'{pfx}ssn',''), nationality1=row.get(f'{pfx}nationality1',''), ph_ct=row.get(f'{pfx}tph_contact_type',''), ph_comm=row.get(f'{pfx}tph_communication_type',''), ph_pfx=row.get(f'{pfx}tph_country_prefix',''), ph_num=row.get(f'{pfx}tph_number',''), a_type=row.get(f'{pfx}addtyp',''), addr_val=row.get(f'{pfx}address',''), city=row.get(f'{pfx}city',''), country=row.get(f'{pfx}country_code',''), state=row.get(f'{pfx}state',''), occupation=row.get(f'{pfx}Occupation',''), role=safe(row.get(f'{pfx}role','ARCTA')), with_is_primary=True, title=safe(row.get(f'{pfx}title','Mr.')))
    if related_accounts_xml is not None: acct.append(related_accounts_xml)
    add(acct, 'opened', safe(row.get(f'{pfx}opened', '')))
    if is_primary_acct: add(acct, 'balance', '')
    add(acct, 'status_code', safe(row.get(f'{pfx}STATUS_CODE', '')))
    add(acct, 'beneficiary_commentooooo', clean_amount(row.get(f'{pfx}_beneficiary_comment', '')))
    add(acct, 'commentsoooo', clean_amount(row.get(f'{pfx}comments', '')))
    c_tag = 'from_country' if 'from' in parent_tag else 'to_country'
    add(wrapper, c_tag, safe(row.get(f'{pfx}to_country', 'PK')))
    return wrapper

# ============ RELATED ACCOUNT BUILDERS ============

def build_entity_related_account(row):
    ara = etree.SubElement(etree.Element('d'), 'account_related_account')
    add(ara, 'account_account_relation', 'AARLO')
    acct = add(ara, 'account')
    add(acct, 'institution_name', safe(row.get('institution_name', 'UNITED BANK LIMITED')))
    add(acct, 'swift', safe(row.get('swift', 'UNILPKKA')))
    add(acct, 'branch', safe(row.get('branch', '')))
    add(acct, 'account', safe(row.get('ACCT_NUM', row.get('account_', ''))))
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


def load_data(p_acct_no, p_trxn_no, p_date_from, p_date_to):
    """Load all 4 data files"""
    # CBS_CC
    trxns , wallet, cbs, entity = fetch_data(p_acct_no, p_trxn_no, p_date_from, p_date_to)
    # cbs = pd.read_csv(CBS_CC_FILE, sep='\t', dtype=str, keep_default_na=False)
    print("1")
    cbs.columns = [c.strip() for c in cbs.columns]
    print("2")

    # WALLET
    # wallet = pd.read_csv(WALLET_FILE, sep='\t', dtype=str, keep_default_na=False)
    wallet.columns = [c.strip() for c in wallet.columns]
    print("3")

    # Merge CBS_CC + WALLET vertically, drop duplicates
    if len(wallet) > 0 and len(wallet.columns) > 1:
        # Align columns
        common_cols = list(set(cbs.columns) & set(wallet.columns))
        ind_linked = pd.concat([cbs[common_cols], wallet[common_cols]], ignore_index=True)
    else:
        ind_linked = cbs.copy()
    print("4")

    ind_linked = ind_linked.drop_duplicates()

    # ENTITY
    # entity = pd.read_csv(ENTITY_FILE, sep='\t', dtype=str, keep_default_na=False)
    print("5")
    
    entity.columns = [c.strip() for c in entity.columns]

    # TRANSACTIONS - handle duplicate column names
    # trxns = pd.read_csv(TRXNS_FILE, sep='\t', dtype=str, keep_default_na=False,
    #                     header=0)
    # Fix duplicate column names - pandas appends .1 to duplicates
    print("6")

    rename_map = {
        'TFMC_customer_Type_code.1': 'TTMC_customer_Type_code',
        'TFMC_customer_Type_desc.1': 'TTMC_customer_Type_desc',
    }
    print("7")

    trxns.rename(columns=rename_map, inplace=True)
    print("8")

    trxns.columns = [c.strip() for c in trxns.columns]
    print("9")
    return ind_linked, entity, trxns

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

def generate_xml(main_account, transaction_number= None, from_date=None, to_date=None):
    logging.info(f"Starting queries execution for account number {main_account}")
    ind_linked, entity, trxns = load_data(main_account, transaction_number, from_date, to_date)
    logging.info(f"Completed queries execution for account number {main_account}")

    main_str = str(main_account).strip()
    ra_block = build_related_accounts(main_account, ind_linked, entity)
    report = etree.Element('report')
    for _, row in trxns.iterrows():
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
        # TFMC - check type, build schema accordingly
        if is_entity(row.get('TFMC_customer_Type_code', '')):
            build_entity_account('t_from_my_client', txn, row, 'TFMC_', related_accounts_xml=tfmc_ra)
        else:
            build_individual_account('t_from_my_client', txn, row, 'TFMC_', related_accounts_xml=tfmc_ra, is_primary_acct=(tfmc_acct == main_str))
        # TTMC - check type, build schema accordingly
        if is_entity(row.get('TTMC_customer_Type_code', '')):
            build_entity_account('t_to_my_client', txn, row, 'TTMC_', related_accounts_xml=ttmc_ra)
        else:
            build_individual_account('t_to_my_client', txn, row, 'TTMC_', related_accounts_xml=ttmc_ra, is_primary_acct=(ttmc_acct == main_str))
    # return report
    logging.info(f"XML genereted for account number {main_account}")
    
    return etree.tostring(report, encoding='unicode')

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
