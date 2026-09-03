"""Typed errors used by the STR generation pipeline."""

from __future__ import annotations

class StrGenerationError(Exception):
    """An expected, classified failure in the STR request pipeline."""

    def __init__(
        self,
        *,
        code: str,
        category: str,
        stage: str,
        message: str,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.category = category
        self.stage = stage
        self.message = message
        self.error_type = error_type

    def as_detail(self) -> dict[str, str]:
        detail = {
            "code": self.code,
            "category": self.category,
            "stage": self.stage,
            "message": self.message,
        }
        if self.error_type:
            detail["error_type"] = self.error_type
        return detail


class NoRecordsFound(StrGenerationError):
    def __init__(self) -> None:
        super().__init__(
            code="NO_RECORDS",
            category="NO_DATA",
            stage="transactions_query",
            message="No STR records were found for the supplied criteria.",
        )


class StrTeradataError(StrGenerationError):
    def __init__(self, stage: str, error: BaseException) -> None:
        if stage == "teradata_connection":
            message = "Failed to connect to Teradata."
        elif stage.endswith("_query"):
            message = "Teradata query failed while retrieving STR data."
        else:
            message = "Teradata operation failed."

        super().__init__(
            code="TERADATA_ERROR",
            category="TERADATA",
            stage=stage,
            message=message,
            error_type=error.__class__.__name__,
        )


class StrProcessingError(StrGenerationError):
    def __init__(
        self,
        stage: str,
        error: BaseException,
        *,
        category: str = "PROCESSING",
        code: str = "STR_PROCESSING_ERROR",
    ) -> None:
        if category == "XML_GENERATION":
            message = "XML generation failed while building the STR report."
        elif category == "INTERNAL":
            message = "An unexpected backend error occurred during STR generation."
        else:
            message = "STR processing failed."

        super().__init__(
            code=code,
            category=category,
            stage=stage,
            message=message,
            error_type=error.__class__.__name__,
        )
