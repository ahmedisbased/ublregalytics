from pydantic import BaseModel
from typing import Optional
from fastapi import File, UploadFile


class StartReportingRequest(BaseModel):
    date : str
    user_id : int


class EndReportingRequest(BaseModel):
    date : str
    user_id : int

