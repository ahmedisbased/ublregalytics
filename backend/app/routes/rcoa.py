from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from ..schemas import (
    EndReportingRequest,
    InsertAdjustmentsFormatRequest,
    InsertRcoaManualDataRequest,
    InsertTfcsSukusRequest,
    RcoaBatchUpdateRequest,
    RcoaBatchUpdateRequestAll,
    RcoaBatchUpdateResponse,
    StartReportingRequest,
    UpdateAdjustmentsFormatRequest,
    UpdateGlSlMappingRequest,
    UpdateLoanTypeSlRequest,
    UpdateRcoaManualDataRequest,
    UpdateSlRcoaMappingRequest,
    UpdateTermDepositMappingRequest,
    UpdateTfcsSukusMappingRequest,
    ViewAdjustmentsFormatRequest,
    ViewGlSlMappingRequest,
    ViewLoanTypeSlRequest,
    ViewRcoaManualDataRequest,
    ViewSlRcoaMappingRequest,
    ViewTermDepositsMappingRequest,
    ViewTfcsSukusMappingRequest,
    AdjustmentsFormatPageResponse,
    AdjustmentsFormatUpdateResponse,
    GlSlMappingPageResponse,
    GlSlMappingUpdateResponse,
    LoanTypePageResponse,
    LoanTypeUpdateResponse,
    RcoaManualDataPageResponse,
    RcoaManualDataUpdateResponse,
    ReportingResponse,
    SlRcoaMappingPageResponse,
    SlRcoaMappingUpdateResponse,
    TermDepositsPageResponse,
    TermDepositsUpdateResponse,
    TfcsSukusPageResponse,
    TfcsSukusUpdateResponse,
)
from ..services import update_gl_sl_mapping as update_gl_sl_mapping_service , start_reporting as start_reporting_service, view_gl_sl_mapping as view_gl_sl_mapping_service
from ..services import end_reporting as end_reporting_service
from ..services import view_term_deposits as view_term_deposits_service, update_term_deposits as update_term_deposits_service
from ..services import view_loan_type_service, update_loan_type_service
from ..services import view_sl_rcoa_mapping_service, update_sl_rcoa_mapping_service
from ..services import view_tfcs_sukus_mapping_service, update_tfcs_sukus_mapping_service
from ..services import view_rcoa_manual_data_service, update_rcoa_manual_data_service
from ..services import view_adjustments_format_service, update_adjustments_format_service
from ..services import insert_adjustments_format, insert_rcoa_manual_data, insert_tfcs_sukus
from ..db import get_db


router = APIRouter()


BATCH_UPDATE_HANDLERS = {
    "gl-sl-mapping": (UpdateGlSlMappingRequest, update_gl_sl_mapping_service),
    "term-deposits": (UpdateTermDepositMappingRequest, update_term_deposits_service),
    "loan-type": (UpdateLoanTypeSlRequest, update_loan_type_service),
    "sl-roca": (UpdateSlRcoaMappingRequest, update_sl_rcoa_mapping_service),
    "tfcs-sukus": (UpdateTfcsSukusMappingRequest, update_tfcs_sukus_mapping_service),
    "rcoa-manual-data": (UpdateRcoaManualDataRequest, update_rcoa_manual_data_service),
    "adjustment": (UpdateAdjustmentsFormatRequest, update_adjustments_format_service),
}







@router.post("/start-reporting", response_model=ReportingResponse)
async def start_reporting(payload : StartReportingRequest, conn = Depends(get_db)):
    if conn is None:
        raise HTTPException(detail = "Database Unavailable" , status_code = 503)
    print(f"connection established successfully")
    print(f" payload is {payload}")
    return start_reporting_service(conn = conn, date = payload.date, user_id = payload.user_id)

@router.post("/end-reporting", response_model=ReportingResponse)
async def end_reporting(payload: EndReportingRequest, conn = Depends(get_db)):
    if conn is None:
        raise HTTPException(detail = "Database Unavailable" , status_code = 503)
    print(f" payload is {payload}")
    return end_reporting_service(conn = conn, date = payload.date, user_id = payload.user_id)

@router.post("/update-gl-sl-mapping", response_model=GlSlMappingUpdateResponse)
async def update_gl_sl_mapping(payload : UpdateGlSlMappingRequest, conn = Depends(get_db)):
    print(f"this is the payload {payload}")
    data = payload.model_dump()
    return update_gl_sl_mapping_service(**data, conn = conn)

@router.post("/view-gl-sl-mapping", response_model=GlSlMappingPageResponse)
async def view_gl_sl_mapping(payload : ViewGlSlMappingRequest, conn = Depends(get_db)):
    print(f"payload is {payload}")
    return view_gl_sl_mapping_service(
        date=payload.date,
        page=payload.page,
        search=payload.search,
        conn=conn,
    )


@router.post("/view-term-deposits", response_model=TermDepositsPageResponse)
async def view_term_deposits(payload : ViewTermDepositsMappingRequest , conn = Depends(get_db)):
    data = payload.model_dump()
    print(f" data is {data}")
    return view_term_deposits_service(**data, conn = conn)

@router.post("/update-term-deposits", response_model=TermDepositsUpdateResponse)
async def update_term_deposits(payload : UpdateTermDepositMappingRequest, conn =  Depends(get_db)):
    data = payload.model_dump()
    return update_term_deposits_service(**data, conn = conn)

@router.post("/view-loan-type", response_model=LoanTypePageResponse)
async def view_loan_type_sl(payload : ViewLoanTypeSlRequest, conn =  Depends(get_db)):
    data = payload.model_dump()
    return view_loan_type_service(**data, conn = conn)

@router.post("/update-loan-type", response_model=LoanTypeUpdateResponse)
async def update_loan_type_sl(payload : UpdateLoanTypeSlRequest, conn = Depends(get_db)):
    data = payload.model_dump()
    print(f"data is {data}")
    return update_loan_type_service(**data, conn = conn)

@router.post("/view-sl-rcoa", response_model=SlRcoaMappingPageResponse)
async def view_sl_rcoa_mapping(payload: ViewSlRcoaMappingRequest, conn=Depends(get_db)):
    data = payload.model_dump()
    print(f"data is {data}")
    return view_sl_rcoa_mapping_service(**data, conn = conn)
    

@router.post("/update-sl-rcoa", response_model=SlRcoaMappingUpdateResponse)
async def view_sl_rcoa_mapping(payload : UpdateSlRcoaMappingRequest , conn = Depends(get_db)):
    data = payload.model_dump()
    print(f"data is {data}")
    return update_sl_rcoa_mapping_service(**data, conn = conn)


@router.post("/view-tfcs-sukus", response_model=TfcsSukusPageResponse)
async def view_tfcs_sukus_mapping(
    payload: ViewTfcsSukusMappingRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return view_tfcs_sukus_mapping_service(**data, conn=conn)


@router.post("/update-tfcs-sukus", response_model=TfcsSukusUpdateResponse)
async def update_tfcs_sukus_mapping(
    payload: UpdateTfcsSukusMappingRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return update_tfcs_sukus_mapping_service(**data, conn=conn)


@router.post("/view-rcoa-manual-data", response_model=RcoaManualDataPageResponse)
async def view_rcoa_manual_data(
    payload: ViewRcoaManualDataRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return view_rcoa_manual_data_service(**data, conn=conn)


@router.post("/update-rcoa-manual-data", response_model=RcoaManualDataUpdateResponse)
async def update_rcoa_manual_data(
    payload: UpdateRcoaManualDataRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return update_rcoa_manual_data_service(**data, conn=conn)


@router.post("/view-adjustments-format", response_model=AdjustmentsFormatPageResponse)
async def view_adjustments_format(
    payload: ViewAdjustmentsFormatRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return view_adjustments_format_service(**data, conn=conn)


@router.post("/update-adjustments-format", response_model=AdjustmentsFormatUpdateResponse)
async def update_adjustments_format(
    payload: UpdateAdjustmentsFormatRequest,
    conn=Depends(get_db),
):
    data = payload.model_dump()
    print(f"data is {data}")
    return update_adjustments_format_service(**data, conn=conn)


@router.post("/insert-adjustments-format", response_model=AdjustmentsFormatUpdateResponse)
def insert_adjustments_format_row(
    payload: InsertAdjustmentsFormatRequest,
    conn=Depends(get_db),
):
    return insert_adjustments_format(**payload.model_dump(), conn=conn)


@router.post("/insert-rcoa-manual-data", response_model=RcoaManualDataUpdateResponse)
def insert_rcoa_manual_data_row(
    payload: InsertRcoaManualDataRequest,
    conn=Depends(get_db),
):
    return insert_rcoa_manual_data(**payload.model_dump(), conn=conn)


@router.post("/insert-tfcs-sukus", response_model=TfcsSukusUpdateResponse)
def insert_tfcs_sukus_row(
    payload: InsertTfcsSukusRequest,
    conn=Depends(get_db),
):
    return insert_tfcs_sukus(**payload.model_dump(), conn=conn)


@router.post("/batch-update-rcoa", response_model=RcoaBatchUpdateResponse)
async def batch_update_rcoa(
    payload: RcoaBatchUpdateRequest,
    conn=Depends(get_db),
):
    if conn is None:
        raise HTTPException(detail="Database Unavailable", status_code=503)

    request_type, update_service = BATCH_UPDATE_HANDLERS[payload.mode]
    updated_rows = []

    try:
        for change in payload.changes:
            typed_change = request_type.model_validate(change)
            result = update_service(**typed_change.model_dump(), conn=conn)
            updated_rows.extend(result.get("data", []))

        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()
    except HTTPException:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
        raise
    except ValidationError as exc:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
        raise HTTPException(detail=exc.errors(), status_code=422) from exc
    except Exception as exc:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
        raise HTTPException(
            detail={"error": str(exc), "message": "Could not save RCOA changes."},
            status_code=503,
        ) from exc

    return {
        "status": "success",
        "updated": len(payload.changes),
        "data": updated_rows,
    }


@router.post("/batch-update-rcoa-all", response_model=RcoaBatchUpdateResponse)
async def batch_update_rcoa_all(
    payload: RcoaBatchUpdateRequestAll,
    conn=Depends(get_db),
):
    if conn is None:
        raise HTTPException(detail="Database Unavailable", status_code=503)
    
    updated_rows = []
    
    try:
        for item in payload.changes:
            if item.mode not in BATCH_UPDATE_HANDLERS:
                raise HTTPException(
                    detail=f"Unsupported RCOA mode: {item.mode}",
                    status_code=422,
                )
            request_type, update_service = BATCH_UPDATE_HANDLERS[item.mode]
            typed_change = request_type.model_validate(item.change)
            result = update_service(**typed_change.model_dump(), conn=conn)
            updated_rows.extend(result.get("data", []))

        commit = getattr(conn, "commit", None)
        if callable(commit):
            commit()
    except HTTPException as e :
        print(str(e))
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
            
        raise
    except ValidationError as exc:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
        raise HTTPException(detail=exc.errors(), status_code=422) from exc
    except Exception as exc:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
        raise HTTPException(
            detail={"error": str(exc), "message": "Could not save RCOA changes."},
            status_code=503,
        ) from exc

   
    return {
        "status": "success",
        "updated": len(payload.changes),
        "data": updated_rows,
    }

    
