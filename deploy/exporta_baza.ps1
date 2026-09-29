# Pe LAPTOP: exportă baza din containerul mip-db într-un fișier .dump (format custom).
# Fișierul se copiază apoi pe server și se importă cu importa_baza.ps1.
#   .\deploy\exporta_baza.ps1                 -> mip_AAAA-LL-ZZ.dump în folderul curent
#   .\deploy\exporta_baza.ps1 -Iesire D:\x.dump
param([string]$Iesire = "mip_$(Get-Date -Format yyyy-MM-dd).dump")
$ErrorActionPreference = "Stop"

docker exec mip-db pg_dump -U mip -d mip -Fc -f /tmp/mip.dump
if ($LASTEXITCODE -ne 0) { throw "pg_dump a eșuat (rulează containerul mip-db?)" }
docker cp mip-db:/tmp/mip.dump $Iesire
if ($LASTEXITCODE -ne 0) { throw "docker cp a eșuat" }
docker exec mip-db rm /tmp/mip.dump | Out-Null

$mb = [math]::Round((Get-Item $Iesire).Length / 1MB, 1)
Write-Host "Scris: $Iesire ($mb MB)"
