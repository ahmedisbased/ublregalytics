from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from .validation import NUMERIC_CODE_PATTERN


class ViewAdjustmentsFormatRequest(BaseModel):
    date: str
    page: int
    search: str | None = None


class UpdateAdjustmentsFormatRequest(BaseModel):
    start_date: str
    sl_code: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    amount: Decimal | None = None
    flag: str | None = None
    original_sl_code: str | None = Field(default=None, pattern=NUMERIC_CODE_PATTERN)
    original_amount: Decimal | None = None
    original_flag: str | None = None

    @model_validator(mode="after")
    def validate_at_least_one_parameter_is_available(self):
        if self.sl_code is None and self.amount is None and self.flag is None:
            raise ValueError("At least one of sl_code, amount, or flag should not be None")
        return self
