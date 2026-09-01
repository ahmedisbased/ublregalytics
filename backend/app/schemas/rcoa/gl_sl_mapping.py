from pydantic import BaseModel, Field
from fastapi import File, UploadFile

from .validation import NUMERIC_CODE_PATTERN
class SaveGlSlMappingRequest(BaseModel):
    file : UploadFile = File(...)


class ViewGlSlMappingRequest(BaseModel):
    date : str
    page : int
    search: str | None = None


class UpdateGlSlMappingRequest(BaseModel):
    gl_edw_id : str
    cury_edw_id : str
    sl_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    start_date : str

