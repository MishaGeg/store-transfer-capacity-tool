# PROJECT_CONTEXT.md — Store Transfer Capacity Visibility Tool
 
*Business-domain reference. Explains the real-world problem, company systems, and data shape the project is built around.*
 
## The problem
 
Misha works as a supply chain manager at a multibrand footwear/accessories retailer (stores carry multiple brands in shared physical space, not hard-walled per brand). When managers redistribute stock between stores, there's no visibility into whether the destination already has enough of that brand to make the transfer sensible — overstocking happens because managers aren't aware of what other managers are simultaneously sending to the same store.
 
BC Central (the company's ERP) handles the actual transfer transaction but has no capacity visibility feature — this tool fills that gap only.
 
## What the tool is (and isn't)
 
- **Is:** a read-only, advisory decision-support layer, checked *before* executing a transfer in BC Central.
- **Isn't:** a system of record for transfers — never executes transfers itself. BC Central remains the transactional source of truth.
- **Isn't:** hard-blocking. Over capacity is a warning, not a rejection — brand space overlaps in real stores.
## Company systems in play
 
- **BC Central** — ERP, system of record for stock and transfers. Direct export access. No capacity-visibility feature.
- **Qlik** — company BI tool, sits on BC Central data. Not used as a v1 data source (no IT-granted API access). Possible future automation for auto-pulling the daily snapshot.
## Data sources
 
1. **Daily stock snapshot** — machine-generated, Excel upload. Columns: `Cat_1`, `Brand_1`, `ST`, `Q-ty` (dated, e.g. `Q-ty \n07/08/2026` — confirms point-in-time snapshots).
2. **Redistribution transfer plan** — human-decided, entered via a live frontend form (not a file upload, to avoid reintroducing typo/stale-template risk and a context-switch out of the browser). UI is a manager-built grid, not a one-row-at-a-time form: brand chosen once via dropdown (governs the whole grid), then manager manually adds/removes from-store and to-store rows/columns via dropdowns (DB-sourced, never free-typed) — default empty scaffold (e.g. 10×10) is a UI convenience only, unrelated to schema. Manager types a quantity directly into a row×column cell to represent a transfer between that store pair. On submit, each non-empty cell becomes one `PlannedTransfer` row (same fields: `from_store_id`, `to_store_id`, `brand`, `quantity`, `submitted_at`) — grid is a bulk-entry UI layer only, doesn't change `PlannedTransfer`'s shape. Diagonal (store → itself) disabled. Chosen over both a single-transfer-at-a-time form (too slow for real volume) and Excel upload (typo/stale-template risk) — grid gives Excel-like bulk-entry speed while keeping DB-sourced dropdown validation.

## Data model (4 tables)
 
- **`Store`** — one table for all locations (stores *and* warehouses). Has a `type` column (`store` / `warehouse`) set at classification time — not inferred from name prefix at query time, since naming isn't reliably classifiable (see Location classification below). No separate `Warehouse` table.
- **`StockSnapshot`** — FK: `store_id`. Current-state table: one row per `(store_id, brand, category)`, composite unique constraint on those three columns. `category` sourced from `Cat_1` in the BC Central export (only `footwear`/`slippers` tracked — see Location classification section for the same filtering discipline applied here). `snapshot_date` is a `DateTime` column showing when the row was last refreshed, not a uniqueness dimension — re-uploading (e.g. after stale Qlik data) **overwrites** the existing row via upsert (update-if-exists, insert-if-new); old values are not retained.
- **`PlannedTransfer`** — FKs: `from_store_id`, `to_store_id` (two separate FKs to `Store`). Fields: brand, quantity, submitted timestamp. No status field, no arrival tracking — see Inbound transfer window below. Permanent historical log, rows never deleted.
- **`BrandCapacity`** — FK: `store_id`. One row per `(store_id, brand)`. Config data, not transactional.
- `brand` is a plain string column on all three data tables above — no `Brand` table, no DB-level brand validation.
**Dependency order:** `Store` first (no outbound FKs). `StockSnapshot`, `PlannedTransfer`, `BrandCapacity` all depend on `Store`; no dependency order among these three relative to each other.
 
**Thinnest vertical slice:** `Store` + `BrandCapacity` + `StockSnapshot`, current stock vs. capacity for one store — no `PlannedTransfer`/inbound logic yet.
 
## Inbound transfer window (capacity check logic)
 
A `PlannedTransfer` counts as "inbound" in the capacity check for a flat **`TRANSFER_INBOUND_WINDOW_DAYS = 5`** from submission (single named constant, no region/local split), then stops contributing to the capacity math. The row itself is never deleted.
 
Rationale: a missed overstock warning (false negative) is worse than a stale warning (false positive) — the tool is advisory only, so a manager double-checking something already resolved costs little. Real lead time: local transfers land in BC Central's snapshot in 1–3 days, regional up to 5 — the flat 5-day window means local transfers occasionally still show as "inbound" for a day or two after arrival, accepted as the safer trade-off.
 
## Snapshot re-upload behavior

Managers may upload a fresh stock snapshot multiple times a day — Qlik data can be stale, and a manager may re-pull before submitting transfers. `StockSnapshot` is designed as a current-state table (not a historical log) to support this: each upload is an **upsert** keyed on `(store_id, brand, category)` — if a row already exists, its `quantity` and `snapshot_date` are updated in place; if not, a new row is created. Prior values are not retained. `snapshot_date` therefore functions as a "last refreshed" timestamp visible to managers, not a historical record — the tool always reflects the latest known stock, never a stale intermediate upload from earlier the same day.

## Excel import row aggregation

The daily Qlik export has multiple rows per `(store, brand, category)` combination — granularity comes from `Cat_2` and `LSC Retail Product Code`, both ignored fields (see Data sources). This means a single upload can contain several raw rows that all map to the same `StockSnapshot` unique key.

Import logic accounts for this with a two-pass approach: all validated rows are first accumulated into an in-memory total, summing `quantity` per `(store_id, brand, category)` key; only after the full file is read does the import call the upsert function once per unique key, with the summed quantity. Calling the upsert function once per raw row (without aggregating first) would silently overwrite rather than combine, undercounting stock whenever a store/brand/category had more than one row in the source file.

## Warehouse handling
 
Warehouses are `Store` rows with `type = 'warehouse'`. They never get a `BrandCapacity` row (or get a symbolic one) and are excluded from capacity checks by querying `type = 'store'` — not by string-matching name prefixes.
 
## Location classification (`ST` field)
 
The `ST` column in BC Central exports mixes stores, warehouses, online channels, and irrelevant entries — not reliably inferable from string patterns alone, confirmed from a real 62-value sample:
 
- **Stores** — majority of values (e.g. `Bata_9 Sab_CityMall`, `ICR_Shoes East_Point`). Each distinct string is an independent real store.
- **Warehouses** — `WH_` prefix is reliable *as a pattern for warehouses specifically* (`WH_Gamarj`, `WH_Konserv`, `WH_Transit`). `WH_Outlet` excluded (not needed).
- **Online channels** — `Online_Okaidi`, `Online_Shop` — excluded, no physical shelf space.
- **Excluded/irrelevant** — e.g. `TR_Wuni` — confirmed not needed.
- **Not inferable from naming** — e.g. `Ecco_Geox_Out`, bare `ICR_Shoes` — irregular-looking but real stores.
Classification requires a manually-built, hand-confirmed lookup table, not a regex/prefix rule. New `ST` values in future exports need the same manual check. Confirmed result of classification is stored as the `type` column on `Store` (see Data model).
 
## `BrandCapacity` entry & sync mechanism
 
- **Editing surface — revised decision:** originally planned as a CSV + manual sync script (`import_capacity.py`). Superseded during P1.5: capacities will be viewed and edited directly through the app's own frontend (React), not a CSV/script workflow — matches the project's decision to keep the whole backend a consistent JSON API (see P1.5 entry below) rather than mixing in a file-based admin process. CSV/script approach not used.
- **Source of truth for queries:** unchanged — a real `BrandCapacity` Postgres table, since the capacity check needs to SQL-join stock/transfer data against capacity in one query.
- **Initial data / current state:** no bulk sync mechanism built yet. Table seeded manually via direct SQL (`INSERT ... SELECT ... FROM stores WHERE name = ...`) in pgAdmin — small real subset (10 rows, one store/brand-group combination each), one-time, same "small real subset" pattern as `seed_stores.py`. This is a stopgap for development, not the long-term entry mechanism.
- **Brand-grouping data reality:** real-world capacity is currently only known at a brand-group level, not per individual brand — e.g. at `ICR_Shoes`, Ecco + Geox + Studio share one combined capacity number, and BATA + BAMBINO share another. Groupings are consistent across all stores for now (not store-specific). Schema stays per-`(store_id, brand)` as designed (no group-level table, no `capacity_type` flag — considered and rejected as overkill) — the seam is in data entry only: every brand in a group gets the same shared capacity number on its own row until real per-brand figures exist, at which point rows are updated individually with no schema change needed. Current seed data uses the literal brand-group label `"ECCOGEOXSTUDIO"` as the `brand` value for grouped rows — note this won't match any single real brand string from Excel imports (`Brand_1`) or `PlannedTransfer` entries; a group-label-to-individual-brand mapping will be needed before capacity-check queries can join across these tables by brand. Not yet designed.

## Glossary
 
| Term | Meaning |
|---|---|
| `ST` | BC Central's store/location field. Requires manual classification before use — see Location classification. |
| `Brand_1` | Primary brand field in BC Central exports; the field brand capacity is tracked against. |
| `Cat_1` / `Cat_2` | Category hierarchy in exports (`Cat_1` broad e.g. FOOTWEAR/BAG, `Cat_2` finer e.g. SNEAK-ATHL/BACKPACK). |
| `Q-ty` | Quantity column, dated in the header — confirms exports are point-in-time snapshots. |
| `BC Central` | Company ERP. Transactional source of truth for stock and transfers. |
| `Qlik` | Company BI tool over BC Central data. Not used as a v1 data source. |
| `Store` | Single table for all locations, disambiguated by `type` column (`store` / `warehouse`). |
| `PlannedTransfer` | Decided transfer, entered via frontend form. Two FKs to `Store` (`from_store_id`, `to_store_id`). No status field, no arrival tracking — see Inbound transfer window. |

## Project setup & implementation status

**Repo:** `https://github.com/MishaGeg/store-transfer-capacity-tool` — separate from an earlier, unrelated project (`retail-report-automation`) that this folder was originally copied from; git history was deliberately reset to avoid carrying over unrelated commits.

**P1.1 — Skeleton + `Store` model: complete.**
- Flask app (`app.py`), config loaded from `.env` via explicit `load_dotenv()` (not relying on editor auto-loading — verified this distinction matters, since VS Code can silently inject `.env` values independent of the app's own code).
- Postgres DB: `store_transfer_capacity_tool`, local install, connected via `psycopg` (v3) driver.
- `Store` model built with a `CheckConstraint` restricting `type` to `('store', 'warehouse')` — chosen over unconstrained free text, since the upstream manual `ST` classification step (P1.3) already guarantees only clean values reach this table; the constraint is a safety net, not a scalability limiter (a third category could still be added later via migration).
- Schema managed via Alembic/Flask-Migrate (not `db.create_all()`) from the first table onward — gives versioned, reviewable schema history.
- Health check route (`/`) verifies actual DB connectivity (`SELECT 1` via `db.session.execute`), not just that Flask is running — returns HTTP 500 on DB failure.

**P1.3 — Excel import route: complete.**
- `POST /import-stock` route: validates `.xlsx` upload, reads `Cat_1`/`Brand_1`/`ST`/`Q-ty` by fixed column position (export column order confirmed stable across dates, so no header-text matching needed).
- Store lookup built as a single upfront query (`{name: id}` dict) to avoid N+1 queries against `Store` per row.
- Per-row validation (empty quantity, unrecognized `ST` value, empty brand) logged to a `skipped` list with row numbers; rows outside `footwear`/`slippers` are filtered silently (expected/routine, not an error). Row aggregation for duplicate keys — see Excel import row aggregation above.
- `update_stock_data` (the upsert function) no longer commits internally; the caller controls when to commit. Import route commits once after all rows are processed.
- Test `Store` data seeded via `seed_stores.py` (upsert-by-`name`) — small real subset, not the full classified list yet.

**Environment notes (for future setup / onboarding reference):**
- Each project should have its own local `.venv/` — a shared/global venv across projects caused contamination (unrelated packages showing up in `pip freeze`) and is not used going forward.
- `requirements.txt` is maintained manually/curated (direct dependencies only, added immediately after each `pip install`) rather than generated via `pip freeze`, to keep it free of transitive-dependency noise.

**P1.4 — `/import-stock` route cleanup: complete.**
- Added per-row exception handling around `int(quantity)` in the row-validation loop: `except (TypeError, ValueError)` catches non-numeric and `None` quantity values, logs to `skipped` with a `"quantity number error"` reason, and `continue`s — critical fix, since without this a single bad row anywhere in a multi-thousand-row file would crash the entire import with a 500 and lose all previously-accumulated `totals` (nothing is staged for commit until the write pass, so it was all-or-nothing).
- Fixed a related counting bug: the `except` block was missing `continue`, so a row that failed quantity conversion was double-counted — once in `skipped`, once in `processed`.
- Refactored the single large `import_stock()` route into three functions across two new/existing files, split by responsibility (read → validate → write):
  - **`snapshot_reader.py`** (new file) — reading/parsing responsibility, separate from persistence:
    - `read_stock_data(file)`: validates `.xlsx` extension (`raise ValueError(...)` on failure, not a Flask response — helpers can't return `jsonify()` meaningfully since they aren't routes), loads the workbook, builds `store_lookup`. Returns `(sheet, store_lookup)`.
    - `validate_stock_data(sheet, store_lookup)`: the per-row validation loop (category filter, empty quantity, unknown `ST`, empty brand, quantity conversion) — moved here unchanged in logic from the original route, only relocated. Returns `(processed, skipped, totals)`.
  - **`snapshot_import.py`** — gained `write_stock_data(totals)`: loops `totals` calling `update_stock_data` per key, single `db.session.commit()` after the loop. Lives alongside `update_stock_data` since both are persistence-layer concerns, distinct from the reading/parsing in `snapshot_reader.py`.
  - **`app.py`** — `import_stock()` is now a thin route: calls `read_stock_data` inside a `try`, catches `ValueError` and returns `jsonify({"error": str(e)}), 400` (reads the actual exception message rather than duplicating the string), then calls `validate_stock_data` and `write_stock_data` in sequence, returns `jsonify({"processed": processed, "skipped": skipped})`.
- Real-file test confirmed the fix works correctly against the actual Qlik export (4000+ rows): bad quantity values logged individually to `skipped` with row numbers, rest of file processes normally, no crash.
- Design principle reinforced this session: file-module boundaries follow *responsibility* (parsing vs. persistence vs. HTTP/routing), not "one function per file" — multiple functions sharing one responsibility belong in the same module.

**P1.5 — `BrandCapacity` model + capacities API (in progress).**
- `BrandCapacity` model built: `id`, `brand` (string), `capacity` (integer), `store_id` (FK to `stores.id`), composite `UniqueConstraint("store_id", "brand")`. `category` deliberately left off for now — real capacity data sometimes splits by category (footwear vs. slippers) and sometimes doesn't (combined), and modeling that ambiguity properly (nullable column vs. a `"combined"` sentinel value vs. other) was deferred until real per-category data exists; current spec text (`PROJECT_CONTEXT.md` data model section) still says one row per `(store_id, brand)`, which matches the model as built.
- Migration generated and applied via `flask db migrate` / `flask db upgrade`.
- Table name fixed to `capacities` (plural convention, matches `stores`).
- **Architecture decision this session:** project standardized on a pure JSON API on the Flask side — no `render_template`/Jinja for new work, going forward. `/import.html`'s existing form page (pre-dates this decision) is a known exception, not the pattern to replicate. Frontend will be a separate React codebase calling JSON routes. Chosen deliberately to mirror real production separation (backend API + independent frontend) rather than course-habit server-rendered pages, and as an opportunity to build React/JS skills alongside backend work. Routes are tested via Postman/browser directly (no HTML form needed for testing).
- Seed data: 10 real `(store, brand-group, capacity)` rows entered manually via raw SQL in pgAdmin (`INSERT ... SELECT ... FROM stores WHERE name = ...`), using `"ECCOGEOXSTUDIO"` as the brand-group label — see entry & sync mechanism above for the open item this creates (group-label-to-brand mapping, not yet designed).
- `GET /capacities` — implemented and tested. Manual SQLAlchemy join (`db.session.query(BrandCapacity, Store).join(Store, BrandCapacity.store_id == Store.id)`, no `relationship()` defined — deliberate, not needed yet) grouped in Python into nested shape `{store_name: [{"brand": ..., "capacity": ...}, ...]}` — chosen over a flat list so the frontend (list of stores → click a store → see/edit its capacity rows) doesn't need to do its own grouping. Grouping logic: `if store_name not in results: results[store_name] = []` followed by unconditional `.append(...)` outside the `if` — every row must add itself to the list regardless of whether the key already existed.
- `PUT /capacities/<int:store_id>/<brand>` — implemented and tested. Both `store_id` and `brand` needed in the URL since the unique constraint is composite (neither alone identifies a row); `<int:store_id>` converter used so Flask both validates and casts the URL segment before the function runs. Looks up the row via `.filter_by(store_id=..., brand=...).first()`, returns 404 with a JSON error body if no match. On match: reads new value from JSON body via `request.get_json()`, reassigns `result.capacity` in place (no `db.session.add()` needed — object was already loaded from a query, so SQLAlchemy is already tracking it), `db.session.commit()` persists the `UPDATE`.
- **Known gap, not yet fixed:** `PUT` route has no input validation on the request body. Confirmed via manual test: sending a non-numeric `capacity` value (e.g. `{"capacity": "aasd"}`) passes through untouched until `db.session.commit()`, where it fails with an uncaught `sqlalchemy.exc.DataError` — and because Flask is running in debug mode, the response is a full Werkzeug interactive debugger page, leaking the raw SQL statement, table/column names, and parameter values (and carrying a live code-execution risk if debug mode were ever exposed outside localhost). Two separate fixes identified, neither done yet: (1) validate `capacity` is a real integer before touching `result`/`commit()`, same pattern as the `except (TypeError, ValueError)` fix from P1.4; (2) confirm/ensure `debug=True` never ships outside local development.

**Not yet done:**
- `PUT /capacities` input validation (see known gap above)
- Debug-mode / production config review
- Frontend (React) for viewing/editing capacities — not started
- Full `ST` classification / complete `Store` table (still only the small test subset)

| `BrandCapacity` | Config table: how much space a brand has at a store. FK to `Store`. Currently seeded manually via SQL; long-term entry mechanism is the app's own frontend — see entry & sync mechanism above. |