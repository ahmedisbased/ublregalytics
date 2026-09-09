"""RCOA-only error boundary and safe error response helpers."""

import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response


logger = logging.getLogger("rcoa")

RCOA_PATHS = frozenset(
    {
        "/rcoa-metadata",
        "/start-reporting",
        "/end-reporting",
        "/view-gl-sl-mapping",
        "/update-gl-sl-mapping",
        "/view-term-deposits",
        "/update-term-deposits",
        "/view-loan-type",
        "/update-loan-type",
        "/view-sl-rcoa",
        "/update-sl-rcoa",
        "/view-tfcs-sukus",
        "/update-tfcs-sukus",
        "/view-rcoa-manual-data",
        "/update-rcoa-manual-data",
        "/view-adjustments-format",
        "/update-adjustments-format",
        "/insert-adjustments-format",
        "/insert-rcoa-manual-data",
        "/insert-tfcs-sukus",
        "/batch-update-rcoa",
        "/batch-update-rcoa-all",
    }
)


def _is_rcoa_request(request: Request) -> bool:
    path = request.url.path.rstrip("/")
    return path in RCOA_PATHS or f"/{path.rsplit('/', 1)[-1]}" in RCOA_PATHS


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "rcoa_request_id", None)
    if existing:
        return existing
    request_id = str(uuid4())
    request.state.rcoa_request_id = request_id
    return request_id


def _default_message(status_code: int) -> str:
    if status_code == 400 or status_code == 422:
        return "The RCOA request contains invalid values."
    if status_code == 403:
        return "You are not authorized to perform this RCOA operation."
    if status_code == 404:
        return "The requested RCOA record was not found."
    if status_code == 503:
        return "RCOA is temporarily unavailable. Try again later."
    return "The RCOA operation could not be completed."


def _error_code(status_code: int) -> str:
    if status_code == 400 or status_code == 422:
        return "RCOA_VALIDATION_ERROR"
    if status_code == 403:
        return "RCOA_FORBIDDEN"
    if status_code == 404:
        return "RCOA_NOT_FOUND"
    if status_code == 503:
        return "RCOA_DATABASE_UNAVAILABLE"
    return "RCOA_OPERATION_FAILED"


def _safe_detail(detail: object, status_code: int, request_id: str) -> dict[str, str]:
    message = ""
    code = ""
    raw_error_present = False
    if isinstance(detail, dict):
        candidate_message = detail.get("message")
        candidate_code = detail.get("error_code")
        raw_error_present = isinstance(detail.get("error"), str)
        if isinstance(candidate_message, str):
            message = candidate_message
        if isinstance(candidate_code, str):
            code = candidate_code
    elif isinstance(detail, str):
        message = detail

    message_lower = message.lower()
    if (
        "unexpected error" in message_lower
        or "gosqldriver" in message_lower
        or message.startswith("[Version")
        or len(message) > 240
        or "\n" in message
        or (raw_error_present and not message)
    ):
        message = ""

    generic_messages = {
        "Database Error",
        "Operational Error",
        "Could not connect to teradata",
        "Database Unavailable",
    }
    if not message or message in generic_messages:
        message = _default_message(status_code)

    return {
        "message": message,
        "error_code": code or _error_code(status_code),
        "request_id": request_id,
    }


def _response(detail: dict[str, str], status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers={"X-Request-ID": detail["request_id"]},
    )


def install_rcoa_error_handling(app: FastAPI) -> None:
    """Install a safe boundary without changing non-RCOA error responses."""

    @app.middleware("http")
    async def rcoa_error_boundary(request: Request, call_next) -> Response:
        if not _is_rcoa_request(request):
            return await call_next(request)

        request_id = _request_id(request)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled RCOA request failure request_id=%s path=%s",
                request_id,
                request.url.path,
            )
            return _response(_safe_detail({}, 500, request_id), 500)

        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(HTTPException)
    async def rcoa_http_exception_handler(request: Request, exc: HTTPException):
        if not _is_rcoa_request(request):
            return await http_exception_handler(request, exc)

        request_id = _request_id(request)
        logger.error(
            "RCOA request failed request_id=%s status=%s path=%s detail=%r",
            request_id,
            exc.status_code,
            request.url.path,
            exc.detail,
        )
        detail = _safe_detail(exc.detail, exc.status_code, request_id)
        return _response(detail, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def rcoa_validation_exception_handler(request: Request, exc: RequestValidationError):
        if not _is_rcoa_request(request):
            return await request_validation_exception_handler(request, exc)

        request_id = _request_id(request)
        logger.warning(
            "RCOA request validation failed request_id=%s path=%s errors=%r",
            request_id,
            request.url.path,
            exc.errors(),
        )
        return _response(
            {
                "message": "The RCOA request contains invalid values.",
                "error_code": "RCOA_VALIDATION_ERROR",
                "request_id": request_id,
            },
            422,
        )
