def search_condition(search: str | None, columns: list[str]) -> str:
    """Build a literal, case-insensitive search condition for a view query."""
    if not search or not search.strip() or search.strip().lower() in {"none", "null"}:
        return ""

    value = search.strip().upper().replace("'", "''")
    expressions = [
        f"UPPER(CAST({column} AS VARCHAR(255))) LIKE '%{value}%'"
        for column in columns
    ]
    return f" AND ({' OR '.join(expressions)})"
