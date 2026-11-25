# Testing

[Project overview](../README.md) · [Local setup](setup.md)

## Run pytest locally

Install the development dependencies and configure `SECRET_KEY` and
`DATABASE_URL` as described in the [setup guide](setup.md).

In pgAdmin, connect to the PostgreSQL server and login in `DATABASE_URL`. Open
the Query Tool for the `postgres` database and run this outside a transaction
if the dedicated test database does not already exist.

```sql
CREATE DATABASE store_transfer_test;
```

Use a dedicated, disposable database. The configured PostgreSQL user needs
permission to create and drop tables in it. Pytest reuses the server and
credentials from `DATABASE_URL` and switches the database name to
`store_transfer_test`. The fixtures call `create_all()` and `drop_all()` around
database tests. They use in-memory rate limits so test resets leave Redis
counters intact.

With the virtual environment activated, run from the project root.

```powershell
python -m pytest
```

The suite covers authentication, permissions, stock imports, shared capacity,
transfer validation, and partial success. The
[sample-workbook integration test](../tests/test_demo.py) exercises the HTTP
endpoints. Browser interactions are outside the pytest suite.

## GitHub Actions

The [workflow](../.github/workflows/tests.yml) starts a disposable PostgreSQL
service. It runs `flask db upgrade head` in the service's empty `postgres`
database, then runs pytest against `store_transfer_test`. This checks the
migration path from an empty database independently of the pytest fixtures.
