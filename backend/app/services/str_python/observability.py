"""Structured logging helpers for STR generation.

The STR endpoint returns these entries to the UI as well as writing them to the
backend logger.  Query text and credentials are deliberately never included.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from collections.abc import Callable
from typing import Any


LogEntry = dict[str, Any]
StatusCallback = Callable[[LogEntry], None]


def status_from_log(entry: LogEntry) -> LogEntry | None:
    """Convert verbose server events into a small set of user-facing milestones."""
    stage = str(entry.get("stage", ""))
    message = str(entry.get("message", ""))
    level = str(entry.get("level", "INFO")).upper()

    if level == "ERROR" and stage != "request":
        if stage == "teradata_connection" or stage.endswith("_query"):
            return {
                "type": "status",
                "timestamp": entry["timestamp"],
                "stage": "error",
                "message": "Teradata error while accessing STR data.",
            }
        if stage in {"xml_build", "xml_generation"}:
            return {
                "type": "status",
                "timestamp": entry["timestamp"],
                "stage": "error",
                "message": "XML generation error while building the STR report.",
            }
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "error",
            "message": "STR processing error.",
        }

    if level == "WARNING" and stage == "transactions_query":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "error",
            "message": "No STR records were found for the supplied criteria.",
        }

    if stage == "xml_generation" and message == "STR XML generation started.":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "starting",
            "message": "Preparing STR XML generation...",
        }
    if stage == "teradata_connection" and message == "Connecting to Teradata.":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "connecting",
            "message": "Connecting to Teradata...",
        }
    if stage == "teradata_connection" and message == "Teradata connection established.":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "connected",
            "message": "Connected to Teradata. Preparing queries...",
        }
    if stage.endswith("_query") and message == "Executing query on Teradata.":
        query_label = stage.replace("_", " ")
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "running_query",
            "message": f"Running {query_label} on Teradata...",
        }
    if stage == "xml_generation" and message == "STR data loading completed; building XML document.":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "building_xml",
            "message": "Query results are ready. Building XML...",
        }
    if stage == "xml_generation" and message == "STR XML generated successfully.":
        return {
            "type": "status",
            "timestamp": entry["timestamp"],
            "stage": "complete",
            "message": "XML generation completed successfully.",
        }
    return None


class StatusLogBuffer(list[LogEntry]):
    """Keep server diagnostics while forwarding only milestone events to a client."""

    def __init__(self, status_callback: StatusCallback) -> None:
        super().__init__()
        self.status_callback = status_callback

    def append(self, entry: LogEntry) -> None:
        super().append(entry)
        status = status_from_log(entry)
        if status is not None:
            self.status_callback(status)


def add_str_log(
    logs: list[LogEntry],
    logger: logging.Logger,
    level: str,
    stage: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> LogEntry:
    """Append one UI-safe log entry and write the same event to the server log."""
    entry: LogEntry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "stage": stage,
        "message": message,
    }
    if details:
        entry["details"] = details

    logs.append(entry)
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        "[STR] stage=%s message=%s details=%s",
        stage,
        message,
        details or {},
    )
    return entry


def mask_account(account_number: object) -> str:
    """Return an account identifier that is useful for tracing but not exposed."""
    value = str(account_number or "").strip()
    if len(value) <= 4:
        return "*" * len(value)
    return f"{'*' * (len(value) - 4)}{value[-4:]}"


def exception_text(error: BaseException) -> str:
    """Return a bounded, credential-safe exception description."""
    text = " ".join(str(error).split())
    if not text:
        text = error.__class__.__name__
    text = re.sub(
        r"(?i)(password|passwd|pwd)\s*[=:]\s*[^,\s]+",
        r"\1=<redacted>",
        text,
    )
    return text[:500]
