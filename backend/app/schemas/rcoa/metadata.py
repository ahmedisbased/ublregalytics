"""RCOA table metadata loaded from the checked-in Teradata HELP TABLE file."""

from functools import lru_cache
from pathlib import Path
import re
from typing import Any


METADATA_PATH = Path(__file__).with_name("metadata.txt")
_TABLE_PATTERN = re.compile(r"^HELP TABLE\s+([A-Za-z0-9_]+\.[A-Za-z0-9_]+);$", re.IGNORECASE)


def _field(fields: list[str], headers: list[str], name: str) -> str:
    """Read a HELP TABLE field despite its header's leading tab."""
    try:
        header_index = headers.index(name)
    except ValueError:
        return ""

    offset = len(headers) - len(fields)
    value_index = header_index - offset
    if value_index < 0 or value_index >= len(fields):
        return ""
    return fields[value_index].strip()


def _parse_metadata() -> dict[str, dict[str, Any]]:
    tables: dict[str, dict[str, Any]] = {}
    current_table: str | None = None
    headers: list[str] = []

    for raw_line in METADATA_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        table_match = _TABLE_PATTERN.match(line)
        if table_match:
            current_table = table_match.group(1).upper()
            tables[current_table] = {"columns": []}
            headers = []
            continue

        if current_table is None:
            continue

        if "Column Name" in raw_line and "Column SQL Name" in raw_line:
            headers = [part.strip() for part in raw_line.split("\t")]
            continue

        fields = raw_line.split("\t")
        if not fields or not fields[0].strip().isdigit() or not headers:
            continue

        column_name = _field(fields, headers, "Column Name")
        sql_name = _field(fields, headers, "Column SQL Name") or column_name
        if not column_name or not sql_name:
            continue

        tables[current_table]["columns"].append(
            {
                "name": column_name,
                "sql_name": sql_name,
                "type": _field(fields, headers, "Type"),
                "nullable": _field(fields, headers, "Nullable") == "Y",
                "max_length": _field(fields, headers, "Max Length"),
                "decimal_total_digits": _field(fields, headers, "Decimal Total Digits"),
                "decimal_fractional_digits": _field(fields, headers, "Decimal Fractional Digits"),
            }
        )

    if not tables or any(not table["columns"] for table in tables.values()):
        raise RuntimeError(f"RCOA metadata is empty or malformed: {METADATA_PATH}")
    return tables


@lru_cache(maxsize=1)
def get_rcoa_metadata() -> dict[str, Any]:
    return {
        "source": METADATA_PATH.name,
        "tables": _parse_metadata(),
    }


def _canonical_table_name(table_name: str) -> str:
    canonical = table_name.strip().upper()
    if canonical not in get_rcoa_metadata()["tables"]:
        raise KeyError(f"Unknown RCOA table: {table_name}")
    return canonical


def table_columns(table_name: str) -> list[dict[str, Any]]:
    return get_rcoa_metadata()["tables"][_canonical_table_name(table_name)]["columns"]


def normalize_column_name(column_name: str) -> str:
    return column_name.strip().strip('"').upper()


def table_column_sql_name(table_name: str, column_name: str) -> str:
    normalized = normalize_column_name(column_name)
    for column in table_columns(table_name):
        if normalize_column_name(column["name"]) == normalized:
            return column["sql_name"]
        if normalize_column_name(column["sql_name"]) == normalized:
            return column["sql_name"]
    raise KeyError(f"Unknown column {column_name} for RCOA table {table_name}")


def table_sql_columns(table_name: str) -> list[str]:
    return [column["sql_name"] for column in table_columns(table_name)]


def table_select_list(table_name: str) -> str:
    return ", ".join(table_sql_columns(table_name))


def table_search_columns(table_name: str, column_names: list[str]) -> list[str]:
    return [table_column_sql_name(table_name, column_name) for column_name in column_names]
