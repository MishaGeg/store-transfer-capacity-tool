# Local setup

[Project overview](../README.md) · [Sample walkthrough](../README.md#try-it-with-sample-stock)

## Prerequisites

Run the commands in PowerShell. After cloning, work from the repository root.

**Docker Compose** requires Git and Docker with Compose. Clone the repo (step 1), configure the environment (step 4), then follow the Docker instructions in steps 5 through 8. Compose supplies Python, PostgreSQL, Redis, and Caddy.

**Local Python** uses all eight steps. Install the following tools first.

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

Keep this project directory open in PowerShell for the remaining commands.

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
DATABASE_URL=postgresql+psycopg://your_db_user:your_db_password@localhost:5432/store_transfer
```

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs Flask session cookies |
| `APP_ENV` | Use `development` for local HTTP. Setting `production` enables HTTPS-only session cookies; HTTPS must be configured separately. Compose defaults to `development`. |
| `DATABASE_URL` | PostgreSQL connection URL used by SQLAlchemy |
| `RATELIMIT_STORAGE_URI` | Login-attempt counter storage; defaults to `memory://` for direct local runs |
| `TRUST_CADDY` | Compose sets this to `1` so Flask trusts one proxy hop for client IP and scheme. Leave it unset when running Flask directly. |
| `docker_pgs_password` | Compose database owner's password (`store_app`), passed unchanged to PostgreSQL |
| `docker_pgs_password1` | Compose application account's password (`store_runtime`), URL-encoded for the connection URL |

Compose builds its own connection URLs from the two Docker password variables.
On first setup, choose distinct owner and runtime passwords and create the
runtime role in step 6. Changing `.env` alone does not change an existing
PostgreSQL password.

Docker Compose runs Redis on its internal network and sets
`RATELIMIT_STORAGE_URI=redis://redis:6379/0` for Flask. Redis has no published host
port and disk persistence is disabled: counters survive app restarts but reset
when Redis restarts. The app waits for PostgreSQL and Redis healthchecks during
startup. The app's `/ready` probe reads the `users` table and checks rate-limit
storage. An empty, readable `users` table passes. Rebuild the app image after updating
dependencies with `docker compose up -d --build` on an existing configured setup.

For the local Python setup, use an existing PostgreSQL login for `your_db_user` and its password for
`your_db_password`. URL-encode reserved characters in the database password
when placing it in the connection URL.

Set `SECRET_KEY` to a long random value in either setup. If Python is installed
locally, you can generate one with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

The application reads environment variables and loads local values from `.env`.
Variables already set in the shell take precedence over `.env` values.
Keep `.env` and real credentials out of Git.

### 5. Create the application database

For Docker, the `db` service creates `store_transfer` when it initializes a
fresh volume. Continue to the Docker migration instructions in step 6.

In pgAdmin, connect to the local PostgreSQL server using the same database login
as `DATABASE_URL`. Open the Query Tool for the existing `postgres` database and
run this statement outside a transaction:

```sql
CREATE DATABASE store_transfer;
```

The login that creates the database owns it and must be able to create and
alter its tables. For an existing setup, use its existing application database
instead of creating another one. These instructions assume the database name
and local server/port shown in the example URL.

### 6. Apply database migrations

Back up existing application data before upgrading. See the [Compose backup and restore guide](backup-and-restore.md) for the Docker procedure. Migration `e4c7a2d9f610`
deletes non-ADULTS capacity rows before removing the capacity `segment` column.
Downgrading cannot restore those deleted rows. For a local Python install, run:

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

On a fresh Docker database, open `psql` as the owner after running migrations:

```powershell
docker compose exec db psql -U store_app -d store_transfer
```

Create the runtime role once. At the password prompt, enter the original
runtime password whose URL-encoded form you placed in `docker_pgs_password1`.

```sql
CREATE ROLE store_runtime LOGIN;
\password store_runtime
```

In the same session, grant access to the application tables and sequences,
then set defaults for objects created by future owner migrations:

```sql
GRANT CONNECT ON DATABASE store_transfer TO store_runtime;
GRANT USAGE ON SCHEMA public TO store_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE users, stores, stock_snapshots, capacities, transfers TO store_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO store_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE store_app IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO store_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE store_app IN SCHEMA public
GRANT USAGE ON SEQUENCES TO store_runtime;
```

Enter `\q` to return to PowerShell.

### 7. Seed locations and create login accounts

For Docker, after applying migrations, run these from the project directory:

```powershell
docker compose run --rm --entrypoint python migrate seed.py
docker compose run --rm --entrypoint python migrate -m flask --app app auth create-user planner --role supply_chain
docker compose run --rm --entrypoint python migrate -m flask --app app auth create-user manager --role store_manager
```

These commands use the database configured in the `migrate` service. Seeding a
fresh database creates 25 stores and 2 warehouses. The account command prompts
for a password and confirmation. The two example accounts let you try both sides
of the [sample transfer](../README.md#try-it-with-sample-stock).

For a local Python setup, start by running:

```powershell
python seed.py
```

This adds the locations configured in `seed.py`; running it again updates
location types without changing accounts. Stock and capacities are not seeded;
import and configure them through the application.

Create a supply-chain account and individual store-manager accounts:

```powershell
python -m flask --app app auth create-user planner --role supply_chain
python -m flask --app app auth create-user manager --role store_manager
```

Each command prompts for a password and confirmation, displaying asterisks
while typing. Passwords are stored as hashes. Existing usernames are rejected.
To reset an existing account's password without changing its role, use the
command for your setup.

```powershell
docker compose run --rm --entrypoint python migrate -m flask --app app auth reset-password manager
```

```powershell
python -m flask --app app auth reset-password manager
```

Run account commands in a terminal with access to the configured app and
database. A successful password reset invalidates that user's existing sessions.

### 8. Start the application

```powershell
python -m flask --app app run
```

Open [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login) and sign in as
`planner` with the password you entered during account creation. This command starts the
local development server. The planner loads React, ReactDOM, and Babel from
unpkg. The pages load their Georgian web font from Google Fonts.

For local Docker Compose, run `docker compose up -d --build` and open
[http://127.0.0.1:8080/login](http://127.0.0.1:8080/login). Caddy listens on
that local address and forwards requests to Gunicorn on the Compose network.
