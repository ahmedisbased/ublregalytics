from pydantic import BaseModel, Field 
from datetime import date
from typing import Optional
from fastapi import File, UploadFile, Form


class CsvSchemaRequest(BaseModel):
    transaction_date: str
    cr_dr_flag: str
    entity_individual_flag: str


class CtrSchemaRequest(BaseModel):
    file : UploadFile = File(...)
    
    

class CTRData(BaseModel):
    cr_dr_flag : str = 'DR'
    transaction_date : Optional[str] = None
    entity_individual_flag : str = 'ENTITY'
