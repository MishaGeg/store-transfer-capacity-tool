# Docker database backup and restore

[Local setup](setup.md) · [Project overview](../README.md)

Run these commands in PowerShell from the project directory with the `db`
service running. This example backs up `store_transfer`. For a practice run,
set `$sourceDb` to a disposable database instead. Keep the archive outside the
repository because it contains application data, including password hashes.

```powershell
$sourceDb = 'store_transfer'
$dumpName = "store-transfer-$([guid]::NewGuid()).dump"
$containerDump = "/tmp/$dumpName"
$backupDir = Join-Path $env:USERPROFILE 'Backups\store-transfer'
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
$restoreDump = "/tmp/store-transfer-restore-$([guid]::NewGuid()).dump"

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
