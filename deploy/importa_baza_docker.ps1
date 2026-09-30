# Pe LAPTOP (Docker): importă în containerul mip-db un .dump făcut cu exporta_baza.ps1.
#   docker compose up -d
#   .\deploy\importa_baza_docker.ps1 -Fisier C:\cale\mip_2026-09-30.dump
#   .\deploy\importa_baza_docker.ps1 -Fisier ... -Baza mip_test_import   # probă, nu atinge `mip`
#
# Nu se pierde nimic: se restaurează întâi în `<Baza>_nou`, iar baza existentă
# nu se atinge până nu reușește restaurarea. Abia apoi se schimbă numele:
#   <Baza>  -> <Baza>_vechi_<AAAAMMZZ_HHmmss>   (rămâne, nu se șterge)
#   <Baza>_nou -> <Baza>
# Aplicația (python app/server.py) trebuie oprită înainte; la final se pornește din nou.
param(
    [Parameter(Mandatory = $true)] [string]$Fisier,
    [string]$Baza = "mip",
    [string]$Container = "mip-db",
    [string]$Utilizator = "mip"
)
$ErrorActionPreference = "Stop"
if ($Baza -notmatch '^[a-z_][a-z0-9_]*$') { throw "Nume de bază nepermis: $Baza (doar a-z, 0-9, _)" }
if (-not (Test-Path $Fisier)) { throw "Nu există: $Fisier" }
$Fisier = (Resolve-Path $Fisier).Path

$stare = docker inspect -f "{{.State.Running}}" $Container
if ($LASTEXITCODE -ne 0 -or $stare -ne "true") { throw "Containerul $Container nu rulează. Pornește-l cu: docker compose up -d" }

$nou = "${Baza}_nou"
$vechi = "${Baza}_vechi_$(Get-Date -Format yyyyMMdd_HHmmss)"
$tinta = "/tmp/import_$Baza.dump"
$tabele = "observatii_curente", "surse", "campanii", "catalog_libra", "app_release"

function sql($q, $db = "postgres") {
    $r = docker exec $Container psql -U $Utilizator -d $db -v ON_ERROR_STOP=1 -tAc $q
    if ($LASTEXITCODE -ne 0) { throw "psql a eșuat: $q" }
    return $r
}
function exista($db) { return [bool](sql "SELECT 1 FROM pg_database WHERE datname = '$db'") }
function inchide($db) {
    sql "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid()" | Out-Null
}
function redenumeste($din, $in) {
    # O conexiune nouă (aplicația pornită, un psql deschis) poate apărea între
    # închidere și redenumire; se reîncearcă de câteva ori.
    if (exista $in) { throw "Există deja o bază '$in'; nu o suprascriu" }
    for ($i = 1; $i -le 5; $i++) {
        inchide $din
        $ErrorActionPreference = "Continue"   # eroarea psql e așteptată aici, se reîncearcă
        docker exec $Container psql -U $Utilizator -d postgres -v ON_ERROR_STOP=1 -tAc "ALTER DATABASE $din RENAME TO $in" 2>&1 | Out-Null
        $cod = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        if ($cod -eq 0) { return }
        Start-Sleep -Seconds 2
    }
    throw "Nu pot redenumi $din în $in (are conexiuni deschise; oprește aplicația și încearcă din nou)"
}
function numara($db) {
    $lista = ($tabele | ForEach-Object { "'$_'" }) -join ","
    # query_to_xml: numără doar tabelele care există (o bază veche poate să nu le aibă pe toate)
    $q = "SELECT t || ': ' || COALESCE((xpath('/row/c/text()', query_to_xml('SELECT count(*) AS c FROM ' || t, false, true, '')))[1]::text, 'lipsește') FROM unnest(ARRAY[$lista]) t WHERE to_regclass(t) IS NOT NULL UNION ALL SELECT t || ': lipsește' FROM unnest(ARRAY[$lista]) t WHERE to_regclass(t) IS NULL"
    return sql $q $db
}

$areVeche = exista $Baza
if ($areVeche) {
    Write-Host "Baza actuală '$Baza' (înainte de import):"
    numara $Baza | ForEach-Object { Write-Host "  $_" }
}

if (exista $nou) {
    Write-Host "Șterg '$nou', rămasă de la un import neterminat (nu e baza ta)."
    inchide $nou
    sql "DROP DATABASE $nou" | Out-Null
}
sql "CREATE DATABASE $nou OWNER $Utilizator ENCODING 'UTF8' TEMPLATE template0" | Out-Null

try {
    docker cp $Fisier "${Container}:$tinta"
    if ($LASTEXITCODE -ne 0) { throw "docker cp a eșuat" }
    Write-Host "Restaurez în '$nou'..."
    docker exec $Container pg_restore -U $Utilizator -d $nou --no-owner --no-privileges --role=$Utilizator --exit-on-error $tinta
    if ($LASTEXITCODE -ne 0) { throw "pg_restore a eșuat; '$Baza' a rămas neatinsă (restul parțial e în '$nou', se șterge la rularea următoare)" }
}
finally {
    docker exec $Container rm -f $tinta | Out-Null
}

if ($areVeche) { redenumeste $Baza $vechi }
try { redenumeste $nou $Baza }
catch {
    if ($areVeche) { redenumeste $vechi $Baza; Write-Host "Am pus la loc '$Baza' (cea veche)." }
    throw
}

Write-Host ""
Write-Host "Import reușit în '$Baza':"
numara $Baza | ForEach-Object { Write-Host "  $_" }
Write-Host ""
if ($areVeche) {
    Write-Host "Baza ta de dinainte a rămas ca '$vechi'."
    Write-Host "Revenire la ea (cu aplicația oprită):"
    Write-Host "  docker exec $Container psql -U $Utilizator -d postgres -c `"ALTER DATABASE $Baza RENAME TO ${Baza}_importat`""
    Write-Host "  docker exec $Container psql -U $Utilizator -d postgres -c `"ALTER DATABASE $vechi RENAME TO $Baza`""
    Write-Host "Ștergerea copiei vechi, doar când ești sigur că noua bază e bună:"
    Write-Host "  docker exec $Container psql -U $Utilizator -d postgres -c `"DROP DATABASE $vechi`""
}
Write-Host "Pornește aplicația din nou: python app/server.py"
