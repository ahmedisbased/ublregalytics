"""
Request schema for /generate-xml.

Backend input validation added as defence-in-depth. The XML query builders
(app/services/str_python/queries.py) currently interpolate these values
directly into SQL strings, e.g.

    AND FACT.ACCT_SROGT_ID = '{p_acct_no}'

which is a SQL-injection sink. The frontend strips inputs to digits, but the
backend must NOT trust the client. These validators reject anything that is not
a legitimate account/transaction/date value before it can reach the query
layer. (The proper long-term fix is parameterised/bind queries - see the
remediation document.)
"""
from pydantic import BaseModel, field_validator
from typing import Optional
import re

_ACCOUNT_RE = re.compile(r"^\d{1,20}$")
# One or more comma-separated numeric transaction ids.
_TXN_RE = re.compile(r"^\d{1,20}(,\d{1,20})*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StrSchemaRequest(BaseModel):
    main_account: str
    transaction_number: Optional[str] = ""
    from_date: Optional[str] = None
    to_date: Optional[str] = None

    @field_validator("main_account")
    @classmethod
    def _validate_account(cls, v: str) -> str:
        v = (v or "").strip()
        if not _ACCOUNT_RE.fullmatch(v):
            raise ValueError("main_account must be 1-20 digits")
        return v

    @field_validator("transaction_number")
    @classmethod
    def _validate_txn(cls, v: Optional[str]) -> str:
        v = (v or "").strip()
        if v == "":
            return ""
        if not _TXN_RE.fullmatch(v):
            raise ValueError("transaction_number must be digits, comma-separated")
        return v

    @field_validator("from_date", "to_date")
    @classmethod
    def _validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _DATE_RE.fullmatch(v):
            raise ValueError("date must be in YYYY-MM-DD format")
        return v
