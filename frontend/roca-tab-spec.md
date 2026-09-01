# ROCA Tab — Front-End Build Spec

> Hand-off doc for a coding agent. The app already has a top-level tabbed page with
> **CTR** and **STR** tabs, shown/hidden per the logged-in user's backend permissions.
> This spec adds a third tab, **ROCA**, following the same permission model and reusing
> existing table / filter / pagination primitives.
>
> ⚠️ Items marked **[ASSUMPTION]** are inferred from a hand-drawn sketch. Replace column
> names, filter values, and the API contract with the real ones before implementing.

---

## 1. Where it fits

Top-level tabs: `ROCA | CTR | STR`

- Render a tab **only** if the user has permission for it (same gate already used for CTR/STR).
- ROCA is a new peer tab. Add `"ROCA"` to whatever permission enum/list drives the existing switch.
- Default selected tab = first tab the user is permitted to see.
- No layout change to CTR/STR. Reuse the same tab container.

```
permissions: string[]   // e.g. ["ROCA", "CTR"]  ->  STR tab hidden
```

---

## 2. ROCA tab anatomy (top → bottom)

1. **Sub-tab / mode selector** — 3 modes (segmented control or secondary tab strip):
   - `GL–SL Mapping`  (map General Ledger accounts to Subsidiary Ledger accounts)
   - `SL ROCA`        (ROCA figures at SL level)
   - `Adjustment`     (manual adjustments)
2. **Filter bar** — scopes the table below. **[ASSUMPTION]** filters apply across all 3 modes:
   - `Product` — single-select toggle: `Deposit | Loan`
   - `Instrument` — single-select: `TFC | Sukuk | Manual`
   - `Search` — free text (GL code / SL code / name)
   - `Apply` and `Reset` buttons
3. **Data table** — columns depend on the active mode (§4).
4. **Pagination** — server-side. `◀ Prev   Page X of N   Next ▶`. The sketch shows "Page 1 of 100", so total pages come from the API, not from a client-side slice.

See `roca-tab-wireframe` for the visual layout.

---

## 3. Component tree

```
<RocaTab>                         // mounted only when permitted
├─ <RocaModeTabs>                 // GL–SL Mapping | SL ROCA | Adjustment
├─ <RocaFilterBar>                // product toggle, instrument select, search, apply/reset
│    props: value, onApply, onReset
├─ <RocaTable>                    // columns switch on active mode; reuse existing DataTable
│    props: mode, rows, loading, onRowAction
└─ <Pagination>                   // reuse existing; server-driven
     props: page, totalPages, onChange
```

Suggested local state (or a small reducer / query-state hook):

```ts
type RocaState = {
  mode: 'gl-sl-mapping' | 'sl-roca' | 'adjustment';
  product: 'deposit' | 'loan';
  instrument: 'tfc' | 'sukuk' | 'manual';
  search: string;
  page: number;          // 1-based
  pageSize: number;      // e.g. 25
};
```

---

## 4. Columns per mode  **[ASSUMPTION — replace with real fields]**

**GL–SL Mapping**

| Column   | Notes                    |
|----------|--------------------------|
| GL Code  | monospace                |
| GL Name  |                          |
| SL Code  | monospace                |
| SL Name  |                          |
| Type     | Deposit / Loan / TFC / Sukuk |
| Balance  | right-aligned, formatted |
| Action   | Edit / Delete            |

**SL ROCA**

| Column   | Notes                    |
|----------|--------------------------|
| SL Code  | monospace                |
| SL Name  |                          |
| Type     |                          |
| Opening  | right-aligned            |
| Debit    | right-aligned            |
| Credit   | right-aligned            |
| Closing  | right-aligned            |

**Adjustment**

| Column     | Notes                  |
|------------|------------------------|
| Date       |                        |
| SL Code    | monospace              |
| Description|                        |
| Amount     | right-aligned          |
| Dr/Cr      | badge                  |
| Status     | badge (Pending/Posted) |
| Action     | Edit / Delete          |

---

## 5. Data contract  **[ASSUMPTION — align with your backend]**

One paginated endpoint per mode, or one endpoint with a `mode` param:

```
GET /api/roca/{mode}
  ?product=deposit|loan
  &instrument=tfc|sukuk|manual
  &search=<string>
  &page=<1-based int>
  &pageSize=<int>

200 ->
{
  "rows": [ /* shape depends on mode, see §4 */ ],
  "page": 1,
  "pageSize": 25,
  "totalPages": 100,
  "totalCount": 2500
}
```

- Pagination is **server-side** — never fetch all rows and slice client-side.
- Send the current filter state as query params on every fetch.

---

## 6. Interaction rules

- Changing **mode** → reset `page` to 1; clear or preserve filters (**[DECISION NEEDED]** — default: preserve product/instrument, clear search).
- Changing any **filter** → do **not** auto-fetch; fetch on `Apply`. `Reset` restores defaults and refetches.
- Changing **page** → fetch immediately with current filters.
- `Prev` disabled on page 1; `Next` disabled on last page.
- Row `Action` (Edit) opens the existing edit flow/modal for that mode. **[ASSUMPTION]**

## 7. States to implement

- **Loading** — skeleton rows or spinner in the table body; keep header + filters visible.
- **Empty** — "No records match these filters." with a Reset shortcut.
- **Error** — inline message with a Retry button; don't blow away filter state.
- **Permission denied** — ROCA tab is simply never rendered (handled at §1), so no in-tab guard is needed.

## 8. Styling / reuse checklist

- Reuse the CTR/STR tab container, table, badge, and pagination components — don't fork them.
- Match existing spacing, typography, and button styles.
- Sentence case for all labels ("GL–SL mapping", not "GL-SL Mapping").
- Right-align numeric columns; monospace codes/amounts.

---

## Open questions to confirm before building

1. Real column list and field names for each of the 3 modes.
2. Are `Deposit/Loan`, `TFC/Sukuk/Manual` global filters, or do they differ per mode?
3. Is `Manual` an instrument value or its own mode?
4. Exact API path(s), page size, and whether filters persist across mode switches.
5. What the row `Edit`/`Adjustment` action does (inline edit vs modal vs new route).
