from pydantic import BaseModel, Field, model_validator

from .validation import NUMERIC_CODE_PATTERN


class ViewTfcsSukusMappingRequest(BaseModel):
    date: str
    page: int
    search: str | None = None


class UpdateTfcsSukusMappingRequest(BaseModel):
    loan_no: str = Field(pattern=NUMERIC_CODE_PATTERN)
    start_date: str
    cust_name: str | None = None
    rcoa_code: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)

    @model_validator(mode="after")
    def validate_at_least_one_parameter_is_available(self):
        if self.cust_name is None and self.rcoa_code is None:
            raise ValueError("Either cust_name or rcoa_code should not be None")
        return self
