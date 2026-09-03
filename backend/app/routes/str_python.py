import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.services import generate_xml, get_current_user
from app.schemas import StrSchemaRequest
from app.services.str_python.errors import (
    NoRecordsFound,
    StrGenerationError,
    StrProcessingError,
    StrTeradataError,
)
from app.services.str_python.observability import (
    StatusLogBuffer,
    add_str_log,
    exception_text,
    mask_account,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _public_logs(logs: list[dict]) -> list[dict]:
    """Keep detailed exception metadata in server logs, not API responses."""
    return [
        {
            "timestamp": entry.get("timestamp"),
            "level": entry.get("level"),
            "stage": entry.get("stage"),
            "message": entry.get("message"),
        }
        for entry in logs
    ]


def _error_detail(error: StrGenerationError, request_id: str, logs: list[dict]) -> dict:
    return {
        **error.as_detail(),
        "request_id": request_id,
        "logs": _public_logs(logs),
    }


def _error_status(error: StrGenerationError) -> int:
    if isinstance(error, NoRecordsFound):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, StrTeradataError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _record_request_error(
    error: StrGenerationError,
    request_id: str,
    logs: list[dict],
) -> None:
    if isinstance(error, NoRecordsFound):
        add_str_log(
            logs,
            logger,
            "WARNING",
            "request",
            "STR request completed without matching records.",
            {"request_id": request_id},
        )
        return

    if isinstance(error, StrTeradataError):
        add_str_log(
            logs,
            logger,
            "ERROR",
            "request",
            "STR request failed because of a Teradata error.",
            {"request_id": request_id, "stage": error.stage},
        )
        logger.exception(
            "STR request %s failed at Teradata stage %s",
            request_id,
            error.stage,
        )
        return

    add_str_log(
        logs,
        logger,
        "ERROR",
        "request",
        "STR request failed during application processing.",
        {"request_id": request_id, "stage": error.stage},
    )
    logger.exception(
        "STR request %s failed during processing stage %s",
        request_id,
        error.stage,
    )


def _run_generation(
    request: StrSchemaRequest,
    logs: list[dict],
    request_id: str,
) -> tuple[str | None, StrGenerationError | None]:
    """Run the blocking STR pipeline and return a classified result."""
    try:
        xml_string = generate_xml(
            **request.model_dump(exclude_none=True),
            logs=logs,
        )
        add_str_log(
            logs,
            logger,
            "INFO",
            "request",
            "STR XML request completed successfully.",
            {"request_id": request_id, "xml_characters": len(xml_string)},
        )
        return xml_string, None
    except NoRecordsFound as error:
        _record_request_error(error, request_id, logs)
        return None, error
    except StrTeradataError as error:
        _record_request_error(error, request_id, logs)
        return None, error
    except StrProcessingError as error:
        _record_request_error(error, request_id, logs)
        return None, error
    except Exception as error:
        classified_error = StrProcessingError(
            "request",
            error,
            category="INTERNAL",
            code="INTERNAL_ERROR",
        )
        add_str_log(
            logs,
            logger,
            "ERROR",
            "request",
            "STR request failed due to an unexpected backend error.",
            {
                "request_id": request_id,
                "error_type": error.__class__.__name__,
                "error": exception_text(error),
            },
        )
        logger.exception("Unexpected STR request failure: %s", request_id)
        return None, classified_error


def _request_logs(
    request: StrSchemaRequest,
    request_id: str,
    logs: list[dict],
) -> None:
    add_str_log(
        logs,
        logger,
        "INFO",
        "request",
        "STR XML request received.",
        {
            "request_id": request_id,
            "account": mask_account(request.main_account),
            "transaction_filter": bool(request.transaction_number),
            "from_date": request.from_date or "not set",
            "to_date": request.to_date or "not set",
        },
    )


@router.post("/generate-xml")
def str_python(request: StrSchemaRequest, current_user: dict = Depends(get_current_user)):
    # Inputs are validated by StrSchemaRequest before reaching this point.
    request_id = str(uuid4())
    logs: list[dict] = []
    _request_logs(request, request_id, logs)
    xml_string, error = _run_generation(request, logs, request_id)
    if error is not None:
        raise HTTPException(
            status_code=_error_status(error),
            detail=_error_detail(error, request_id, logs),
        ) from error
    return {"xml": xml_string, "request_id": request_id, "logs": logs}


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


@router.post("/generate-xml/stream")
async def str_python_stream(
    request: StrSchemaRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stream only coarse STR progress milestones while Teradata work runs."""
    request_id = str(uuid4())
    event_queue: asyncio.Queue[dict] = asyncio.Queue()
    event_loop = asyncio.get_running_loop()

    def publish_status(event: dict) -> None:
        event_loop.call_soon_threadsafe(
            event_queue.put_nowait,
            {**event, "request_id": request_id},
        )

    logs = StatusLogBuffer(publish_status)
    _request_logs(request, request_id, logs)

    async def event_stream():
        generation_task = asyncio.create_task(
            asyncio.to_thread(_run_generation, request, logs, request_id),
        )
        heartbeat_at = asyncio.get_running_loop().time() + 10
        yield _sse_event({
            "type": "status",
            "request_id": request_id,
            "stage": "starting",
            "message": "Starting STR XML generation...",
        })

        while not generation_task.done() or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                if asyncio.get_running_loop().time() >= heartbeat_at:
                    heartbeat_at = asyncio.get_running_loop().time() + 10
                    yield ": keep-alive\n\n"
                continue
            yield _sse_event(event)

        # Let callbacks scheduled from the worker thread reach the queue.
        await asyncio.sleep(0)
        while not event_queue.empty():
            yield _sse_event(event_queue.get_nowait())

        xml_string, error = await generation_task
        if error is not None:
            yield _sse_event({
                "type": "error",
                "request_id": request_id,
                "error": error.as_detail(),
            })
            return

        yield _sse_event({
            "type": "complete",
            "request_id": request_id,
            "xml": xml_string,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
