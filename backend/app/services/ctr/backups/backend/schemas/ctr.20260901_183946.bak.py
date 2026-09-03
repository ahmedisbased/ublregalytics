from pydantic import BaseModel, Field 
from datetime import date
from typing import Literal, Optional
from fastapi import File, UploadFile, Form


class CsvSchemaRequest(BaseModel):
    transaction_date: str
    cr_dr_flag: str
    entity_individual_flag: str


class CsvBatchSchemaRequest(BaseModel):
    from_date: date
    to_date: date
    cr_dr_flag: Literal["DR", "CR"]
    entity_individual_flag: Literal["ENTITY", "INDIVIDUAL"]


class CtrSchemaRequest(BaseModel):
    file : UploadFile = File(...)
    
    

class CTRData(BaseModel):
    cr_dr_flag : str = 'DR'
    transaction_date : Optional[str] = None
    entity_individual_flag : str = 'ENTITY'
