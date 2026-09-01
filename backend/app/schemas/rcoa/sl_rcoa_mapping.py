from pydantic import BaseModel, Field, model_validator

from .validation import NUMERIC_CODE_PATTERN


class ViewSlRcoaMappingRequest(BaseModel):
    date : str
    page : int
    search: str | None = None



class UpdateSlRcoaMappingRequest(BaseModel):
    sl_code : str 
    rcoa_code: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    description : str | None = None
    start_date : str
    original_rcoa_code: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    original_description: str | None = None
    @model_validator(mode = "after")
    def validate_at_least_one_parameter_is_available(self):
        if self.description is None and self.rcoa_code is None:
            raise ValueError("Either description or rcoa_code should not be None")
        return self

