from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel


class ReportingResponse(RootModel[int]):
    """The reporting procedures return a numeric success result."""

    root: int


class RcoaPaginationResponse(BaseModel):
    currentPage: int
    pageSize: int
    totalRecords: int
    totalPages: int


class RcoaRowResponse(BaseModel):
    """Base row model that keeps additional columns returned by SELECT *."""

    model_config = ConfigDict(extra="allow")


class GlSlMappingRowResponse(RcoaRowResponse):
    GL_EDW_ID: Any = None
    GL_DESCRIPTION: Any = None
    CURY_EDW_ID: Any = None
    SL_CODE: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class TermDepositsRowResponse(RcoaRowResponse):
    GL_EDW_ID: Any = None
    CURY_EDW_ID: Any = None
    DEP_TERM_TYPE: Any = None
    DEP_TERM_PRD: Any = None
    SL_CODE: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class LoanTypeRowResponse(RcoaRowResponse):
    SL_CODE: Any = None
    LOAN_TYPE: Any = None
    LOAN_TYPE_DESC: Any = None
    CURY_EDW_ID: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class SlRcoaMappingRowResponse(RcoaRowResponse):
    SL_CODE: Any = None
    RCOA_CODE: Any = None
    DESCRIPTION: Any = None
    TIER: Any = None
    DOMAIN: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class TfcsSukusRowResponse(RcoaRowResponse):
    LOAN_NO: Any = None
    CUST_NAME: Any = None
    RCOA_CODE: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class RcoaManualDataRowResponse(RcoaRowResponse):
    FLAG: Any = None
    RCOA_CODE: Any = None
    DOMAIN: Any = None
    AMOUNT: Any = None
    TIER: Any = None
    PARTICULARS: Any = None
    PARTICULARS_DEFINITION: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    START_DATE: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class AdjustmentsFormatRowResponse(RcoaRowResponse):
    START_DATE: Any = None
    SL_CODE: Any = None
    AMOUNT: Any = None
    FLAG: Any = None
    START_TS: Any = None
    END_TS: Any = None
    UPDATE_TS: Any = None
    END_DATE: Any = None
    UPDATE_DATE: Any = None
    RECORD_DELETED_FLAG: Any = None
    SYSTEM_CODE: Any = None
    PROCESS_NAME: Any = None
    UPDATE_PROCESS_NAME: Any = None
    ROW_HASH: Any = None


class GlSlMappingPageResponse(BaseModel):
    data: list[GlSlMappingRowResponse]
    pagination: RcoaPaginationResponse


class TermDepositsPageResponse(BaseModel):
    data: list[TermDepositsRowResponse]
    pagination: RcoaPaginationResponse


class LoanTypePageResponse(BaseModel):
    data: list[LoanTypeRowResponse]
    pagination: RcoaPaginationResponse


class SlRcoaMappingPageResponse(BaseModel):
    data: list[SlRcoaMappingRowResponse]
    pagination: RcoaPaginationResponse


class TfcsSukusPageResponse(BaseModel):
    data: list[TfcsSukusRowResponse]
    pagination: RcoaPaginationResponse


class RcoaManualDataPageResponse(BaseModel):
    data: list[RcoaManualDataRowResponse]
    pagination: RcoaPaginationResponse


class AdjustmentsFormatPageResponse(BaseModel):
    data: list[AdjustmentsFormatRowResponse]
    pagination: RcoaPaginationResponse


class GlSlMappingUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[GlSlMappingRowResponse]


class TermDepositsUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[TermDepositsRowResponse]


class LoanTypeUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[LoanTypeRowResponse]


class SlRcoaMappingUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[SlRcoaMappingRowResponse]


class TfcsSukusUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[TfcsSukusRowResponse]


class RcoaManualDataUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[RcoaManualDataRowResponse]


class AdjustmentsFormatUpdateResponse(BaseModel):
    status: str
    message: str
    data: list[AdjustmentsFormatRowResponse]


class RcoaBatchUpdateResponse(BaseModel):
    status: str
    updated: int
    data: list[RcoaRowResponse]
