from fastapi import APIRouter, HTTPException
from app.services import generate_xml
from app.schemas import StrSchemaRequest

router = APIRouter()

@router.post("/str_python")
def str_python(request: StrSchemaRequest):

    # return generate_xml(account_number, transaction_ids, from_date, to_date)
    xml_string =  generate_xml(**request.model_dump(exclude_none= True))
    return {'xml':xml_string}