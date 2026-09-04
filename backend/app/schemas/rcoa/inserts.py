from decimal import Decimal

from pydantic import BaseModel, Field

from .validation import CUSTOMER_NAME_PATTERN, NUMERIC_CODE_PATTERN


class InsertAdjustmentsFormatRequest(BaseModel):
    start_date: str
    sl_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    amount: Decimal
    flag: str


class InsertRcoaManualDataRequest(BaseModel):
    start_date: str
    rcoa_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    domain: str = Field(pattern=NUMERIC_CODE_PATTERN)
    tier: str = Field(pattern=NUMERIC_CODE_PATTERN)
    amount: Decimal
    flag: str
    particulars: str
    particulars_definition: str


class InsertTfcsSukusRequest(BaseModel):
    start_date: str
    loan_no: str = Field(pattern=NUMERIC_CODE_PATTERN)
    cust_name: str = Field(pattern=CUSTOMER_NAME_PATTERN)
    rcoa_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
