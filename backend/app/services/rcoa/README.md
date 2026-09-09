# RCOA Project Documentation

This document describes the RCOA feature end to end. It covers the FastAPI
routes, Teradata tables, metadata contract, React page, editing workflow,
reporting workflow, error handling, and maintenance process.

## 1. Scope

RCOA is the date-scoped regulatory data workspace mounted by the main
application. It supports these datasets:

| Frontend mode | Teradata table | Main purpose |
| --- | --- | --- |
| GL-SL mapping | `DT_SDMT_UBL.GL_SL_MAPPING` | Map GL records to SL codes |
| Term deposits | `DT_SDMT_UBL.RCOA_TD_MAPPING` | Maintain term-deposit SL mappings |
| Loan type | `DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING` | Maintain loan-type SL mappings |
| SL ROCA | `DT_SDMT_UBL.SL_RCOA_MAPPING` | Maintain SL to RCOA assignments |
| TFCs / Sukuks | `DT_SDMT_UBL.RCOA_ADVANCES_MAPPING` | Maintain customer and RCOA mappings |
| Manual RCOA data | `DT_SDMT_UBL.RCOA_MANUAL_DATA` | Maintain manual amount/domain/tier data |
| Adjustment | `DT_SDMT_UBL.RCOA_SL_WISE_ADJ` | Maintain SL adjustment data |

Reporting operations use stored procedures rather than tables:

| Operation | Stored procedure |
| --- | --- |
| Start reporting | `DT_SDMT_UBL.SP_RCOA` |
| End reporting | `DT_SDMT_UBL.RCOA_SBP_REPORT_SP` |

This documentation is intentionally limited to RCOA. Other application
features such as CTR and STR are outside its scope.

## 2. Directory Map

### Backend

| Path | Responsibility |
| --- | --- |
| `backend/app/routes/rcoa.py` | RCOA HTTP endpoints and batch dispatch |
| `backend/app/services/rcoa/` | Teradata view, update, insert, reporting, and query services |
| `backend/app/services/rcoa/errors.py` | RCOA-only safe error boundary and request IDs |
| `backend/app/services/rcoa/insert_rows.py` | Insert SQL and current insertion-date handling |
| `backend/app/services/rcoa/query_helpers.py` | Search condition construction |
| `backend/app/schemas/rcoa/metadata.txt` | Checked-in Teradata HELP TABLE source contract |
| `backend/app/schemas/rcoa/metadata.py` | Parser and metadata lookup helpers |
| `backend/app/schemas/rcoa/*.py` | Request, validation, insert, and response schemas |

### Frontend

| Path | Responsibility |
| --- | --- |
| `frontend/src/pages/Rcoa/rcoa.tsx` | Complete RCOA workspace and interaction state |
| `frontend/src/pages/Rcoa/rcoa.scss` | RCOA layout, status, modal, table, and responsive styles |
| `frontend/src/services/rcoaService.ts` | RCOA API client and TypeScript response types |

## 3. Metadata Source Of Truth

The authoritative schema input is:

```text
backend/app/schemas/rcoa/metadata.txt
```

It contains the Teradata `HELP TABLE` output for all seven RCOA tables. The
file must be updated whenever a table column is added, removed, renamed, or
changed from quoted to unquoted SQL syntax.

`metadata.py` reads that file and exposes:

| Helper | Purpose |
| --- | --- |
| `get_rcoa_metadata()` | Return all parsed table metadata for the API |
| `table_columns(table)` | Return ordered metadata records for one table |
| `table_column_sql_name(table, column)` | Resolve a logical column to its exact SQL name |
| `table_sql_columns(table)` | Return the ordered SQL column list |
| `table_select_list(table)` | Build an explicit SELECT projection |
| `table_search_columns(table, columns)` | Resolve search columns through metadata |

The frontend loads the same contract through:

GET /rcoa-metadata
```

Each mode contains a `tableName` that matches the metadata table key. The
frontend uses the metadata order and only creates table columns from metadata.
Configured labels, editability, number formats, and input fields are applied
only when the configured key exists in the metadata contract. A column that is
not in metadata is not rendered.

The backend view services use explicit metadata-backed SELECT lists instead of
`SELECT *`. This prevents a new or unexpected database column from silently
changing the API response shape.

### Metadata table columns

#### `DT_SDMT_UBL.GL_SL_MAPPING`

```text
GL_EDW_ID
GL_DESCRIPTION
CURY_EDW_ID
SL_CODE
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

#### `DT_SDMT_UBL.RCOA_TD_MAPPING`

```text
GL_EDW_ID
CURY_EDW_ID
DEP_TERM_PRD
DEP_TERM_TYPE
SL_CODE
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

#### `DT_SDMT_UBL.RCOA_LOAN_TYPE_MAPPING`

```text
LOAN_TYPE
LOAN_TYPE_DESC
CURY_EDW_ID
SL_CODE
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

#### `DT_SDMT_UBL.SL_RCOA_MAPPING`

```text
SL_CODE
RCOA_Code
DESCRIPTION
"DOMAIN"
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

`TIER` is not part of this table and must not be added to the SL RCOA mode,
search list, response schema, or SQL query.

#### `DT_SDMT_UBL.RCOA_ADVANCES_MAPPING`

```text
loan_no
CUST_NAME
RCOA_CODE
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

#### `DT_SDMT_UBL.RCOA_MANUAL_DATA`

```text
RCOA_CODE
"Domain"
Tier
AMOUNT
Flag
Particulars
Particulars_definition
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

#### `DT_SDMT_UBL.RCOA_SL_WISE_ADJ`

```text
SL_CODE
AMOUNT
FLAG
START_TS
END_TS
UPDATE_TS
START_DATE
END_DATE
UPDATE_DATE
RECORD_DELETED_FLAG
SYSTEM_CODE
PROCESS_NAME
UPDATE_PROCESS_NAME
ROW_HASH
```

## 4. HTTP API

The RCOA router is included without a URL prefix. The frontend calls these
paths directly through the configured API base URL.

### Metadata

```http
GET /rcoa-metadata
```

This endpoint reads the checked-in `metadata.txt` file and does not require a
Teradata connection.

### Reporting

```http
POST /start-reporting
POST /end-reporting
```

Request shape:

```json
{
  "date": "2026-09-07",
  "user_id": 123
}
```

`/start-reporting` calls `SP_RCOA`. `/end-reporting` calls
`RCOA_SBP_REPORT_SP`.

### View endpoints

```http
POST /view-gl-sl-mapping
POST /view-term-deposits
POST /view-loan-type
POST /view-sl-rcoa
POST /view-tfcs-sukus
POST /view-rcoa-manual-data
POST /view-adjustments-format
```

View request shape:

```json
{
  "date": "2026-09-07",
  "page": 1,
  "search": "optional search text"
}
```

View responses contain `data` and server-side `pagination`:

```json
{
  "data": [],
  "pagination": {
    "currentPage": 1,
    "pageSize": 20,
    "totalRecords": 0,
    "totalPages": 1
  }
}
```

### Update endpoints

```http
POST /update-gl-sl-mapping
POST /update-term-deposits
POST /update-loan-type
POST /update-sl-rcoa
POST /update-tfcs-sukus
POST /update-rcoa-manual-data
POST /update-adjustments-format
```

The frontend stages updates locally and sends them through one of these
endpoints via `/batch-update-rcoa-all`. The backend validates each change with
the mode-specific Pydantic request model before running it.

### Insert endpoints

```http
POST /insert-adjustments-format
POST /insert-rcoa-manual-data
POST /insert-tfcs-sukus
```

The frontend builds the insertion date at the time the Insert button is
submitted. The backend independently uses its current date for `START_DATE`,
`START_TS`, `END_DATE`, `END_TS`, and update date/timestamp values. This keeps
the insertion-date rule authoritative on the server.

## 5. Frontend Workspace

The page is a single stateful workspace with these layers:

1. Reporting hero with selected date and start action.
2. Reporting status strip.
3. Mode tabs.
4. Mode heading and edit/insert actions.
5. Date, search, and action filters.
6. Notice and safe error banners.
7. Metadata-ordered table.
8. Server-side pagination.
9. End-reporting action.

Rows are identified through each mode's `getRowKey` function. Edits are first
stored in `pendingChanges`, displayed locally, and only written after the user
clicks Save changes.

## 6. Reporting State Machine

The frontend exposes these statuses:

| Status | Meaning |
| --- | --- |
| Not started | No successful start procedure has completed in this page session |
| In progress | Start procedure succeeded and the cycle is active |
| Ending | End procedure is currently running |
| Completed | End procedure succeeded and the cycle is closed |
| Failed | The most recent start or end procedure failed |

The failed action is retained so the UI can offer the correct retry path. A
failed start can be retried. A failed end can be retried. Starting cannot be
re-run after a failed end without changing/resetting the reporting date.

The button next to each reporting action displays the reason it is disabled.
Examples include:

```text
Start reporting before ending the cycle.
Save 2 pending changes before ending reporting.
Your user ID is not available yet.
Reporting has already completed.
```

Before the end procedure runs, the user must confirm a dialog showing:

```text
Selected date
Pending changes
Current status
```

The dialog warns that the reporting cycle cannot be edited after completion.

## 7. Search Behavior

Search is server-side. Typing does not issue a request for every keystroke.
The frontend waits 400 milliseconds after the last change and then updates the
applied search. Pressing Enter or Apply performs the update immediately.

The backend builds search expressions only from metadata-resolved columns. A
search value is escaped before being placed in the current query expression.
Column identifiers are never accepted from the browser.

For future hardening, replace literal search values with Teradata parameter
bindings when the driver contract for each query is standardized.

## 8. Error Handling

All RCOA paths pass through `services/rcoa/errors.py`.

For an RCOA failure, the browser receives only this shape:

```json
{
  "detail": {
    "message": "RCOA is temporarily unavailable. Try again later.",
    "error_code": "RCOA_DATABASE_UNAVAILABLE",
    "request_id": "b3e7c4d7-7c79-43d6-9ec0-4d4b2b2f2d0c"
  }
}
```

The raw Teradata exception and detailed driver text are logged on the backend
with the same request ID. They are never copied into the response detail.
The response also includes an `X-Request-ID` header.

The frontend displays the short message, error code, and request ID. It does
not read or display the raw `error` field from legacy service exceptions.

### Error code meanings

| Code | Meaning |
| --- | --- |
| `RCOA_VALIDATION_ERROR` | Input or request validation failed |
| `RCOA_FORBIDDEN` | The operation was rejected by permissions or the procedure |
| `RCOA_NOT_FOUND` | The requested row was not found |
| `RCOA_DATABASE_UNAVAILABLE` | Teradata or the connection pool is unavailable |
| `RCOA_OPERATION_FAILED` | An unexpected RCOA operation failure occurred |

When reporting an issue, provide the request ID, selected date, active mode,
operation, and approximate time. Do not copy credentials or connection
strings.

## 9. Validation Rules

Validation occurs in both frontend and backend layers.

| Field | Rule |
| --- | --- |
| Numeric codes | ASCII digits only where the schema uses `NUMERIC_CODE_PATTERN` |
| Customer name | Non-empty ASCII letters `A-Z` and `a-z` only |
| Date | `YYYY-MM-DD` format |
| Manual amount | Decimal number |
| Required insert fields | Must be present before the insert request is sent |

The customer-name input removes characters outside `A-Z` and `a-z` while the
user types or pastes. The backend still rejects invalid values so clients
other than this frontend cannot bypass the rule.

## 10. Date and Edit Rules

The report date controls which existing records are viewed and edited. The
frontend allows edits only inside the configured one-month window and before
the reporting cycle is completed.

Insertions use the actual insertion date on the backend. This is separate from
the report date currently selected in the table. After inserting while viewing
an older report date, the new row will be visible when the current insertion
date is selected.

The end-reporting action is disabled while any pending local changes exist.
Users must save changes before the final reporting procedure can run.

## 11. Security and SQL Rules

1. Never accept a table name or column name from the browser.
2. Resolve identifiers through `metadata.py` or a fixed service constant.
3. Keep quoted identifiers exactly as supplied by Teradata metadata.
4. Do not return raw driver exception text in an HTTP response.
5. Keep detailed database diagnostics in server logs only.
6. Validate permissions in backend routes and database procedures; hiding a
   frontend button is not an authorization boundary.
7. Avoid logging passwords, access tokens, or connection strings.
8. Prefer parameter binding for values such as dates, search text, names, and
   descriptions as the query services are modernized.

## 12. How To Add A Column

When a Teradata table changes:

1. Run `HELP TABLE database.table;` in Teradata.
2. Replace that table's block in `backend/app/schemas/rcoa/metadata.txt`.
3. Run the metadata parser check described below.
4. Add or remove the frontend mode configuration only if the field should be
   editable or have a special display format.
5. Confirm that all update and insert payload fields exist in metadata.
6. Run backend compilation and the frontend build.
7. Review the generated table headers manually for the affected mode.

If a column is removed from Teradata, remove it from metadata first. The
frontend will then stop rendering it and metadata-backed query construction
will fail early during development instead of sending invalid SQL.

## 13. Verification Commands

Run from the backend directory:

```powershell
python -m compileall -q app
python -c "from app.schemas.rcoa.metadata import get_rcoa_metadata; print(get_rcoa_metadata())"
```

Run from the frontend directory:

```powershell
npx tsc -b --pretty false
npx eslint src/pages/Rcoa/rcoa.tsx src/services/rcoaService.ts
npm run build
```

The full repository lint command may include unrelated legacy backup files.
Use targeted RCOA lint when checking this feature, then address unrelated
lint failures separately.

## 14. Troubleshooting

### Metadata fails to load

Check that `backend/app/schemas/rcoa/metadata.txt` exists in the deployed
package and that it contains a HELP TABLE header followed by column rows for
all seven tables. The frontend will fail closed rather than show an
unverified column list.

### Search fails with a Teradata syntax error

Check the request ID in the UI, then search backend logs for that ID. Compare
the generated search column list with `metadata.txt`. Pay special attention
to quoted SQL names such as `"DOMAIN"` and `"Domain"`.

### A reporting operation fails

Record the request ID, date, user ID, and whether the failed action was Start
or End. The frontend status is `Failed` and exposes the appropriate retry
action. The backend log contains the procedure error details.

### A row is not visible after insertion

Insertions use the actual insertion date. Select that date in the Report date
filter and reload the active mode. Confirm that the backend response did not
return a request ID error.

## 15. Change Ownership Rules

Changes to `metadata.txt` are schema changes and should be reviewed with the
Teradata owner. Changes to reporting procedure calls should be reviewed with
the reporting owner. Frontend-only label or formatting changes can be made in
`rcoa.tsx`, but a new column must exist in metadata before it is added to a
mode definition.
