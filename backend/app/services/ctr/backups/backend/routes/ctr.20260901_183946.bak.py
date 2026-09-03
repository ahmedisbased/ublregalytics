from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from ..services import generate_ctr_xml, generate_ctr_csv
from ..services.ctr import generate_ctr_csv_batch, generate_ctr_xml_batch
from ..schemas import CsvBatchSchemaRequest, CsvSchemaRequest
from typing import List



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


@router.post("/csv/batch")
async def csv_batch(request: CsvBatchSchemaRequest):
    if request.from_date > request.to_date:
        raise HTTPException(status_code=400, detail="from_date must be before to_date")

    try:
        return generate_ctr_csv_batch(
            from_date=request.from_date.isoformat(),
            to_date=request.to_date.isoformat(),
            cr_dr_flag=request.cr_dr_flag,
            entity_individual_flag=request.entity_individual_flag,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ctr/batch")
async def ctr_batch(
    files: List[UploadFile] = File(...),
    data: str = Form(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one CSV file is required")
    return await generate_ctr_xml_batch(files=files, data=data)
