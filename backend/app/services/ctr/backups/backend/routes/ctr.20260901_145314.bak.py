from fastapi import APIRouter, HTTPException, Request, File, UploadFile, Form
from ..services import generate_ctr_xml, generate_ctr_csv
from ..schemas import CtrSchemaRequest, CsvSchemaRequest,CTRData
from typing import Optional
import json
import pandas as pd
import io



router = APIRouter()


from pydantic import BaseModel


@router.post("/ctr")
async def ctr(
    
    file : UploadFile = File(...),
    # # transaction_date: str = ''
    data : str = Form(...)
    # entity_individual_flag: str = 'ENTITY'
    # request : Request
):
    response =  await generate_ctr_xml(file = file, data = data)
    return response
   
@router.post("/csv")
async def csv(request : CsvSchemaRequest):

    return generate_ctr_csv(**request.model_dump(exclude_none=True))