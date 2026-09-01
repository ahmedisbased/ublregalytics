from fastapi import APIRouter, Depends, HTTPException, status

from app.services import generate_xml, get_current_user
from app.services.str_python.fetch_data_working import NoRecordsFound
from app.schemas import StrSchemaRequest

router = APIRouter()


@router.post("/generate-xml")
def str_python(request: StrSchemaRequest, current_user: dict = Depends(get_current_user)):
    # Inputs are validated by StrSchemaRequest before reaching this point.
    try:
        xml_string = generate_xml(**request.model_dump(exclude_none=True))
    except NoRecordsFound:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "NO RECORDS")
    return {"xml": xml_string}
4