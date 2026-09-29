# Pe SERVER, ca administrator: aplicația ca serviciu Windows, cu NSSM
# (nssm.cc; un singur .exe, fără instalare). Pornește la boot și repornește la cădere.
#   .\deploy\instaleaza_serviciu.ps1 -Radacina D:\mcc\mip -Nssm D:\mcc\nssm.exe
param(
    [string]$Radacina = "D:\mcc\mip",
    [string]$Nssm = "D:\mcc\nssm.exe",
    [string]$Python = (Get-Command python).Source,
    [string]$Serviciu = "MCC",
    [string]$Postgres = "postgresql-x64-16"
)
$ErrorActionPreference = "Stop"
$loguri = Join-Path $Radacina "loguri"
New-Item -ItemType Directory -Force $loguri | Out-Null

& $Nssm install $Serviciu $Python (Join-Path $Radacina "app\server.py")
& $Nssm set $Serviciu AppDirectory $Radacina
& $Nssm set $Serviciu AppEnvironmentExtra "PYTHONIOENCODING=utf-8"
& $Nssm set $Serviciu AppStdout (Join-Path $loguri "server.log")
& $Nssm set $Serviciu AppStderr (Join-Path $loguri "server.log")
& $Nssm set $Serviciu AppRotateFiles 1
& $Nssm set $Serviciu AppRotateBytes 10485760
& $Nssm set $Serviciu DependOnService $Postgres
& $Nssm set $Serviciu Start SERVICE_AUTO_START
& $Nssm set $Serviciu DisplayName "Marketing Command Center"
Start-Service $Serviciu

Start-Sleep -Seconds 3
$r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8765/index.html"
Write-Host "Serviciul $Serviciu rulează (HTTP $($r.StatusCode) pe 127.0.0.1:8765)."
