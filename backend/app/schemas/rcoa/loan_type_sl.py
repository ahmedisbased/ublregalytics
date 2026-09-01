from pydantic import BaseModel, Field

from .validation import NUMERIC_CODE_PATTERN



class ViewLoanTypeSlRequest(BaseModel):
    date : str
    page : int
    search: str | None = None


class UpdateLoanTypeSlRequest(BaseModel):
    sl_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    loan_type : str
    cury_edw_id : str
    start_date : str

    
