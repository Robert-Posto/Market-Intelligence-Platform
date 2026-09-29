# Pe SERVER: importă un .dump făcut cu exporta_baza.ps1.
#   .\deploy\importa_baza.ps1 -Fisier D:\mcc\mip_2026-09-29.dump
#
# Nu atinge baza curentă până nu reușește importul: restaurează în `mip_nou`,
# apoi schimbă numele (mip -> mip_vechi, mip_nou -> mip). Copia anterioară
# rămâne ca `mip_vechi` până la importul următor, ca să se poată reveni:
#   ALTER DATABASE mip RENAME TO mip_stricat; ALTER DATABASE mip_vechi RENAME TO mip;
param(
    [Parameter(Mandatory = $true)] [string]$Fisier,
    [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
    [string]$Serviciu = "MCC"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Fisier)) { throw "Nu există: $Fisier" }

$env:PGHOST = "localhost"; $env:PGUSER = "postgres"
$p = Read-Host "Parola utilizatorului postgres" -AsSecureString
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))

function sql($q) {
    $r = & "$PgBin\psql.exe" -d postgres -v ON_ERROR_STOP=1 -tAc $q
    if ($LASTEXITCODE -ne 0) { throw "psql a eșuat: $q" }
    return $r
}
function inchide($baza) {
    sql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$baza' AND pid <> pg_backend_pid()" | Out-Null
}

try {
    inchide "mip_nou"
    sql "DROP DATABASE IF EXISTS mip_nou" | Out-Null
    sql "CREATE DATABASE mip_nou OWNER mip ENCODING 'UTF8' TEMPLATE template0" | Out-Null
    & "$PgBin\pg_restore.exe" -d mip_nou --no-owner --no-privileges --role=mip --exit-on-error $Fisier
    if ($LASTEXITCODE -ne 0) { throw "pg_restore a eșuat; baza curentă a rămas neatinsă" }

    Stop-Service $Serviciu -ErrorAction SilentlyContinue
    inchide "mip"; inchide "mip_vechi"
    sql "DROP DATABASE IF EXISTS mip_vechi" | Out-Null
    if (sql "SELECT 1 FROM pg_database WHERE datname = 'mip'") {
        sql "ALTER DATABASE mip RENAME TO mip_vechi" | Out-Null
    }
    sql "ALTER DATABASE mip_nou RENAME TO mip" | Out-Null
    Start-Service $Serviciu -ErrorAction SilentlyContinue

    $n = & "$PgBin\psql.exe" -d mip -tAc "SELECT count(*) FROM observatii_curente"
    Write-Host "Import reușit. Valori curente: $n. Copia anterioară: mip_vechi."
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
