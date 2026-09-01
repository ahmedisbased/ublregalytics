from pydantic import BaseModel, Field

from .validation import NUMERIC_CODE_PATTERN



class ViewTermDepositsMappingRequest(BaseModel):
    date : str
    page : int
    search: str | None = None

class UpdateTermDepositMappingRequest(BaseModel):
    gl_edw_id : str
    sl_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    cury_edw_id : str
    dep_term_type : str
    dep_term_prd : str
    start_date : str

