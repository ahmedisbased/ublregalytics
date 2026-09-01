from typing import Any, Literal

from pydantic import BaseModel, Field


RcoaMode = Literal[
    "gl-sl-mapping",
    "term-deposits",
    "loan-type",
    "sl-roca",
    "tfcs-sukus",
    "rcoa-manual-data",
    "adjustment",
]


class RcoaBatchUpdateRequest(BaseModel):
    mode: RcoaMode
    changes: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class RcoaBatchUpdateItem(BaseModel):
    mode: RcoaMode
    change: dict[str, Any]


class RcoaBatchUpdateRequestAll(BaseModel):
    changes: list[RcoaBatchUpdateItem] = Field(min_length=1, max_length=700)
