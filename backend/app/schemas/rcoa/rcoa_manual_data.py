from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from .validation import NUMERIC_CODE_PATTERN


class ViewRcoaManualDataRequest(BaseModel):
    date: str
    page: int
    search: str | None = None


class UpdateRcoaManualDataRequest(BaseModel):
    rcoa_code: str = Field(pattern=NUMERIC_CODE_PATTERN)
    start_date: str
    amount: Decimal | None = None
    domain: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    tier: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    original_domain: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    original_tier: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)

    @model_validator(mode="after")
    def validate_at_least_one_parameter_is_available(self):
        if self.amount is None and self.domain is None and self.tier is None:
            raise ValueError("At least one of amount, domain, or tier should not be None")
        return self
