# Store Transfer Capacity Visibility Tool

A Flask application that helps supply chain specialists check destination
capacity before planning stock transfers.

Supply chain specialists can import current stock from Excel, configure store
capacities, and record planned transfers. A read-only page lets store
managers view details of planned incoming transfers.

The application supports planning, but it does not execute transfers in CRM.

## Technology Stack

- Python and Flask — backend application and HTTP routes
- PostgreSQL — database for stores, stock, capacities, users, and transfers
- Flask-SQLAlchemy — interaction with the database through Python models
- Flask-Migrate — database schema migrations
- Flask-Login — user authentication and login sessions
- openpyxl — reading Excel stock files
- Jinja templates, JavaScript, and React — web interface

## Prerequisites

- Python 3.14 (tested with 3.14.3)
- PostgreSQL running locally, with a database login allowed to create databases
- pgAdmin for the database-creation steps below
- Git
- Windows PowerShell and the Python launcher (`py`)

## Setup (Windows PowerShell)

### 1. Clone the repository

```powershell
git clone https://github.com/MishaGeg/store-transfer-capacity-tool.git
cd store-transfer-capacity-tool
```

Run the remaining PowerShell commands from this project folder.

### 2. Create and activate a virtual environment

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of
`python` in the commands below; activation is a convenience, not a requirement.

### 3. Install dependencies

```powershell
python -m pip install -r requirements-dev.txt
```

### 4. Configure the environment

For a fresh clone, copy the placeholder file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your local values. Do not overwrite an existing `.env` when
updating an already configured checkout.

```dotenv
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg://your_db_user:your_db_password@localhost:5432/store_transfer_capacity_tool
```

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs Flask session cookies |
| `APP_ENV` | Use `development` for local HTTP. Setting `production` enables HTTPS-only session cookies; HTTPS must be configured separately. Compose defaults to `development`. |
| `DATABASE_URL` | PostgreSQL connection URL used by SQLAlchemy |
| `RATELIMIT_STORAGE_URI` | Login-attempt counter storage; defaults to `memory://` for direct local runs |
| `docker_pgs_password` | Compose database owner's password (`store_app`), passed unchanged to PostgreSQL |
| `docker_pgs_password1` | Compose application account's password (`store_runtime`), URL-encoded for the connection URL |

Compose expects `store_runtime` to exist with application table and sequence
permissions. Changing `.env` does not create roles or change existing database
passwords. Run schema migrations separately as the database owner; the runtime
account has no schema-management permissions.

Docker Compose runs Redis on its internal network and sets
`RATELIMIT_STORAGE_URI=redis://redis:6379/0` for Flask. Redis has no published host
port and disk persistence is disabled: counters survive app restarts but reset
when Redis restarts. The app waits for PostgreSQL and Redis healthchecks during
startup; `/ready` checks both dependencies. Rebuild the app image after updating
dependencies with `docker compose up -d --build` on an existing configured setup.

Use an existing PostgreSQL login for `your_db_user` and its password for
`your_db_password`. URL-encode reserved characters in the database password
when placing it in the connection URL.

Generate a random value for `SECRET_KEY` with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

The application reads environment variables and loads local values from `.env`.
Variables already set in the shell take precedence over `.env` values.
Keep `.env` and real credentials out of Git.

### 5. Create the application database

In pgAdmin, connect to the local PostgreSQL server using the same database login
as `DATABASE_URL`. Open the Query Tool for the existing `postgres` database and
run this statement outside a transaction:

```sql
CREATE DATABASE store_transfer_capacity_tool;
```

The login that creates the database owns it and must be able to create and
alter its tables. For an existing setup, use its existing application database
instead of creating another one. These instructions assume the database name
and local server/port shown in the example URL.

### 6. Apply database migrations

**Existing installs only:** back up application data before upgrading. Migration `e4c7a2d9f610`
deletes non-ADULTS capacity rows before removing the capacity `segment` column.
Downgrading cannot restore those deleted rows.

```powershell
python -m flask --app app db upgrade
```

Migration `27db4bdd6a21` assigns existing accounts the `supply_chain` role.
New accounts require an explicit role.

For Docker Compose, use the separate owner-only migration service. Check the
current revision without changing the schema:

```powershell
docker compose run --rm --build migrate current
```

After backing up an existing database, apply migrations with:

```powershell
docker compose run --rm --build migrate
```

This temporary container connects as `store_app`; the running web app continues
to use `store_runtime`. The `tools` profile keeps migrations out of ordinary
`docker compose up` startup. The owner password is supplied through `PGPASSWORD`,
so `docker_pgs_password` stays unencoded. The container is removed when finished.

For future application tables and sequences, run these once as `store_app` in
the target database, after creating `store_runtime`:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE store_app IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO store_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE store_app IN SCHEMA public
GRANT USAGE ON SEQUENCES TO store_runtime;
```

These defaults apply to objects subsequently created by `store_app` in `public`.
Existing tables and sequences require their own grants.

### 7. Seed locations and create login accounts

For Docker, after applying migrations, run these from the project directory:

```powershell
docker compose run --rm --entrypoint python migrate seed.py
docker compose run --rm --entrypoint python migrate -m flask --app app auth create-user misha --role supply_chain
```

These commands use the database configured in the `migrate` service. Seeding a
fresh database creates 25 stores and 2 warehouses. The account command prompts
for a password and confirmation. To create a viewing account, use a different
username and `--role store_manager`.

For a local Python setup, start by running:

```powershell
python seed.py
```

This adds the locations configured in `seed.py`; running it again updates
location types without changing accounts. Stock and capacities are not seeded;
import and configure them through the application.

Create a supply-chain account and individual store-manager accounts:

```powershell
python -m flask --app app auth create-user misha --role supply_chain
python -m flask --app app auth create-user anna --role store_manager
```

Each command prompts for a password and confirmation, displaying asterisks
while typing. Passwords are stored as hashes. Existing usernames are rejected.
To reset an existing account's password without changing its role, use the
command for your setup.

```powershell
docker compose run --rm --entrypoint python migrate -m flask --app app auth reset-password anna
```

```powershell
python -m flask --app app auth reset-password anna
```

These commands require administrator terminal access to the configured app;
they are not website endpoints. Account passwords are not read from `.env`.

### 8. Start the application

```powershell
python -m flask --app app run
```

Open [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) and sign in as
`misha` with the password you entered during account creation. This command starts the
local development server. The transfers page also needs access to its React,
Babel, and styling/font CDNs.

For local Docker Compose, run `docker compose up -d --build` and open
[http://127.0.0.1:8080/login](http://127.0.0.1:8080/login). Caddy listens on
that local address and forwards requests to Gunicorn on the Compose network.

## Docker Database Backup and Restore

Run these commands in PowerShell from the project directory with the `db`
service running. This example backs up `store_transfer`. For a practice run,
set `$sourceDb` to a disposable database instead. Keep the archive outside the
repository because it contains application data, including password hashes.

```powershell
$sourceDb = 'store_transfer'
$dumpName = "project1-$([guid]::NewGuid()).dump"
$containerDump = "/tmp/$dumpName"
$backupDir = Join-Path $env:USERPROFILE '.codex\backups\Project1'
$backupFile = Join-Path $backupDir $dumpName

docker compose exec -T db pg_dump -U store_app -Fc -f $containerDump $sourceDb
if ($LASTEXITCODE -ne 0) { throw 'Database dump failed.' }

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
docker compose cp "db:${containerDump}" $backupFile
if ($LASTEXITCODE -ne 0) { throw 'Backup copy failed.' }

$containerHash = (docker compose exec -T db sha256sum $containerDump) -split '\s+' |
    Select-Object -First 1
if ($LASTEXITCODE -ne 0) { throw 'Could not hash the container archive.' }
if ((Get-FileHash -LiteralPath $backupFile -Algorithm SHA256).Hash -ne $containerHash) {
    throw 'Backup hashes do not match.'
}
```

To test recovery, copy the saved Windows archive into the container and restore
it into a new database on the same PostgreSQL server. In a new PowerShell window,
set `$backupFile` to the full path of the saved archive first.

```powershell
$restoreDb = 'store_transfer_restore_check'
$restoreDump = "/tmp/project1-restore-$([guid]::NewGuid()).dump"

docker compose exec -T db createdb -U store_app $restoreDb
if ($LASTEXITCODE -ne 0) { throw 'Could not create an empty restore database.' }

docker compose cp $backupFile "db:${restoreDump}"
if ($LASTEXITCODE -ne 0) { throw 'Could not copy the backup into the container.' }

docker compose exec -T db pg_restore -U store_app --exit-on-error --single-transaction -d $restoreDb $restoreDump
if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }

docker compose exec -T db psql -U store_app -d $restoreDb -c "SELECT type, COUNT(*) FROM stores GROUP BY type ORDER BY type;" -c "SELECT username, role FROM users ORDER BY username;"
```

Compare the restored location counts and accounts with the expected values for
that backup. For the seed data in this repo, the expected counts are 25 stores
and 2 warehouses.

## Using the Application

The main pages are:

| Page | Path | Access |
| --- | --- | --- |
| Login | `/login` | Public |
| Plan transfers | `/transfers-page` | Supply chain |
| Import stock | `/import-stock` | Supply chain |
| Edit capacities | `/edit-capacities` | Supply chain |
| View planned transfers | `/public-transfers` | Both roles, login required, read-only |

1. Sign in at `/login` as a supply chain specialist and import the current stock workbook.
2. Configure shared capacities for the destination locations.
3. Select an age group and brand on the transfers page, enter quantities for
   source/destination pairs, and submit. Correct any rejected rows after partial success.
4. Store managers sign in and open `/public-transfers` to view planned incoming transfers
   and filter by destination store.

Saved transfer cells are locked. To change a saved transfer, delete it and
submit a replacement. Drag store headers or row labels to reorder the grid;
the order is saved in the browser's local storage.

The viewing page can filter incoming transfers by destination store. Both
the page and its API require login. The viewing page and the management grid
show transfers submitted within the last five days.
The filter is a display convenience, not a restriction to one manager's store.
Supply-chain users see management navigation; store managers see viewing and logout only.

### Try it with sample stock

On a fresh local database, upload [the sample workbook](samples/stock_sample.xlsx),
then set `ICR_Shoes East_Point`'s `ECCOGEOXSTUDIO` capacity to **100**. On the
transfers page, select **ADULTS → ECCO** and submit **5** from `ICR_Shoes` to
`ICR_Shoes East_Point`. Destination free space changes from **90** to **85**;
the plan also appears on `/public-transfers`.

The workbook contains six rows with synthetic quantities for three seeded
locations. Importing it replaces matching stock quantities, so use a local
demo database rather than operational stock data.

## Business Rules

The API and database use `segment` for the age group: `ADULTS` or `KIDS`.

### Available space

```text
Available space = configured group capacity
                  - current group FOOTWEAR stock
                  - group inbound planned quantities submitted in the last five days
```

Slippers do not count toward capacity. Outbound plans are not subtracted from
current stock. At five days, plans stop reserving space and disappear from both
transfer lists. Their records remain in the database. Negative available space
indicates a shortfall.

### Shared capacity groups

The current catalog assigns the following brand/age-group pairs to shared
capacity groups at each location:

| Capacity group | Brand / age-group pairs |
| --- | --- |
| `ECCOGEOXSTUDIO` | ECCO/ADULTS, GEOX/ADULTS, STUDIO/ADULTS, REPLAY/ADULTS |
| `BATABAMBINO` | BATA/ADULTS, BAMB/KIDS, ECCO/KIDS, GEOX/KIDS |
| `SCARPIERA` | SCARPIERA/ADULTS |

These assignments are defined in `BRAND_AGE_GROUP` in [catalog.py](catalog.py).
They can be added, removed, or reassigned as business requirements change;
the table above reflects the current configuration.

Stock and transfers contain individual brand names. Capacity records contain
group labels. For example, ECCO Adults and ECCO Kids use different groups.

### Transfer eligibility

Retail sources require positive FOOTWEAR stock for the exact selected brand
and age group. Retail destinations require positive configured capacity for
that pair's group; zero or unset capacity hides the destination column. Warehouses always appear
as sources and destinations. A warehouse without configured capacity has
unknown available space (`null`), rather than zero.

Capacity warnings are advisory; they do not block transfer submission. The
submission API does not enforce the grid's stock/capacity eligibility rules.

## Excel Stock Imports

Upload an `.xlsx` workbook on `/import-stock` after signing in. The importer
reads the active worksheet and skips its first row as a header.

- **Columns:** A = category, D = brand, E = location name, F = age group,
  G = quantity. Location names must match existing database records.
- **Accepted stock:** ADULTS FOOTWEAR/SLIPPERS and KIDS FOOTWEAR. Other
  categories and age groups are silently excluded.
- **Updates:** duplicate rows are summed by location, brand, category, and age
  group. Totals replace matching stock quantities; omitted records remain unchanged.
- **Results:** the page shows accepted-row counts and skipped-row reasons.
  The request-size limit is 5 MiB, including upload overhead.

## Design Decisions

- **Advisory capacity:** supply chain specialists retain the final decision
  about a plan. The tool provides capacity guidance; actual transfers happen in CRM.
- **Shared capacity groups:** the grouped brand/age-group combinations occupy
  the same physical store space, so their stock consumes one shared capacity.
- **Partial-success submissions:** valid rows can be saved while rejected rows
  are returned for correction. Clients must inspect both `created` and `errors`.

CRM is the system of record for transaction history; this tool maintains
working plans, so deleting a plan removes it permanently without an audit trail.
There is no update endpoint: changing a saved transfer means deleting it and
submitting a replacement. Older plans remain listed until explicitly deleted.

## Project Structure

| Component | Responsibility |
| --- | --- |
| `app.py` | Configuration, extensions, blueprint registration, and shared error handlers |
| `models.py` | Database models and constraints |
| `catalog.py` | Brand/age-group mappings and shared capacity groups |
| `transfers.py` | Transfer APIs, grid options, and available-space calculation |
| `capacities.py` | Capacity listing and updates |
| `stock_snapshot.py` | Excel loading, validation, aggregation, and stock persistence |
| `stores.py` / `user.py` | Store listing, session authentication, and account CLI commands |
| `permissions.py` | Supply-chain route permission checks |
| `seed.py` | Location seeding |
| `templates/` | Jinja pages with inline styles and JavaScript |
| `migrations/` | Alembic database schema history |
| `tests/` | pytest tests and database fixtures |

The browser calls Flask routes; SQLAlchemy reads and writes PostgreSQL. Pages
are rendered with Jinja. The transfers page loads React and Babel from CDNs
and has no frontend build step.

Use Flask-Migrate/Alembic for application schema changes. Test fixtures use
`create_all()`/`drop_all()` instead and therefore do not verify migrations.

## API Reference

Authentication uses session cookies: sign in through `POST /login` and retain
the cookie for protected requests. Login and logout are public. `/view-transfers`
allows either logged-in role; the remaining data APIs require `supply_chain`.
Forbidden management requests return HTTP 403. Successful login includes a
role-specific `next_page` for browser navigation. Send JSON bodies except
for Excel uploads, which use multipart form data.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/login` | Sign in with `username` and `password` |
| POST | `/logout` | End the login session |
| GET | `/stores` | List stores and warehouses |
| GET | `/transfer-options?brand=ECCO&segment=ADULTS` | Get eligible locations and destination free space |
| GET | `/transfers` | List planned transfers from the last five days |
| POST | `/transfers` | Submit a batch of planned transfers |
| DELETE | `/transfers/<id>` | Permanently delete a planned transfer |
| GET | `/view-transfers` | Authenticated read-only list of transfers with location names |
| GET | `/capacities` | List shared capacities by location |
| PUT | `/capacities/<store_id>/<brand>` | Set a capacity with `{"capacity": 125}`; `brand` is a group label |
| POST | `/import-stock` | Upload an `.xlsx` file in form field `file` |
| GET | `/current-stock` | List stored stock quantities |
| GET | `/last-stock-update` | Get the newest stock timestamp |

Transfer submission expects `{"transfers": [...]}`. Each row needs `brand`,
`segment`, `quantity`, `from_store_id`, and `to_store_id`. The response contains
`created` and `errors`: `201` means full success, `207` partial success, and
`400` no accepted rows or an invalid batch structure. Row-error indexes start
at zero. Transfers require a valid catalog pair, a whole-number quantity from
1 through 2,147,483,647, and two different existing stores with integer IDs.
Capacity values must be integers from 0 through 2,147,483,647.

## Testing

Tests use pytest and a separate PostgreSQL database named `store_transfer_test`.
In pgAdmin, connect to the same PostgreSQL server and login used by the
application, open the Query Tool for `postgres`, and run outside a transaction:

```sql
CREATE DATABASE store_transfer_test;
```

Use an existing dedicated test database if it is already configured. The
database user in `DATABASE_URL` must have permission to create and drop its tables.

The test configuration loads `DATABASE_URL` from the environment or `.env`
and replaces its database name with `store_transfer_test`, keeping the same
connection credentials and server details. Application imports also require
`SECRET_KEY` to be configured for authentication tests.

**Use a dedicated, disposable test database. Tests create tables before each
test that uses the database fixture and drop them afterward. Do not store
application data in `store_transfer_test`.**

With the dependencies installed and the virtual environment activated, run
from the project folder:

```powershell
python -m pytest
```

Tests cover authentication, transfer validation and partial success, catalog
mapping, shared capacity calculations, location eligibility, and stock imports'
validation/persistence helpers. A sample-workbook integration test covers upload,
capacity configuration, transfer submission, and authenticated viewing. The pytest
suite does not provide browser automation or migration coverage.

## Current Limitations

- Failed data requests can appear as empty lists rather than visible errors.
- Unsaved drafts are kept by brand and can carry across age groups; reloading
  discards them. Saved transfers retain their own age group.
- Dates use server-local time without explicit timezone conversion, and the UI
  mixes Georgian and English.
- Deleted plans have no audit history.
