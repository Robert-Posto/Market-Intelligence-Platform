# Pe SERVER, după conectarea prin Remote Desktop: verifică dacă serverul e gata
# pentru instalare (docs/DEPLOY.md). Doar citește, nu instalează și nu schimbă nimic.
#   powershell -ExecutionPolicy Bypass -File .\verifica_server.ps1
# (sau copiezi conținutul direct într-o fereastră PowerShell)

function linie($ce, $ok, $detaliu) {
    $semn = if ($ok) { "[OK]  " } else { "[--]  " }
    Write-Host ("{0}{1,-34} {2}" -f $semn, $ce, $detaliu)
}

Write-Host "`n=== Sistem ==="
$os = Get-CimInstance Win32_OperatingSystem
linie "Windows" $true "$($os.Caption) (build $($os.BuildNumber))"
$cs = Get-CimInstance Win32_ComputerSystem
linie "Domeniu" $cs.PartOfDomain "$($cs.Domain)"
linie "Procesoare / memorie" $true ("{0} nuclee logice, {1:N1} GB RAM" -f $cs.NumberOfLogicalProcessors, ($cs.TotalPhysicalMemory / 1GB))
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
linie "Rulat ca administrator" $admin $(if ($admin) { "da" } else { "nu - instalarea cere drepturi de admin" })
linie "PowerShell" $true "$($PSVersionTable.PSVersion)"

Write-Host "`n=== Discuri (e nevoie de ~3 GB liberi) ==="
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $liber = $_.FreeSpace / 1GB
    linie "Disc $($_.DeviceID)" ($liber -ge 3) ("{0:N1} GB liberi din {1:N1} GB" -f $liber, ($_.Size / 1GB))
}

Write-Host "`n=== Programe ==="
foreach ($p in "python", "git", "psql", "docker") {
    $c = Get-Command $p -ErrorAction SilentlyContinue
    linie $p ([bool]$c) $(if ($c) { $c.Source } else { "lipsește" })
}
$pg = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
linie "Serviciul PostgreSQL" ([bool]$pg) $(if ($pg) { ($pg | ForEach-Object { "$($_.Name): $($_.Status)" }) -join ", " } else { "neinstalat" })
if (Get-Command Get-WindowsFeature -ErrorAction SilentlyContinue) {
    foreach ($f in "Web-Server", "Web-Windows-Auth", "Web-Url-Auth") {
        $x = Get-WindowsFeature $f
        linie "IIS: $f" $x.Installed $(if ($x.Installed) { "instalat" } else { "neinstalat" })
    }
} else {
    linie "IIS" $false "Get-WindowsFeature indisponibil (nu e Windows Server?)"
}
$rew = Test-Path "$env:SystemRoot\System32\inetsrv\rewrite.dll"
linie "IIS URL Rewrite" $rew $(if ($rew) { "instalat" } else { "neinstalat" })

Write-Host "`n=== Rețea ==="
foreach ($u in "https://github.com", "https://pypi.org", "https://www.postgresql.org") {
    try {
        $r = Invoke-WebRequest -Uri $u -Method Head -UseBasicParsing -TimeoutSec 15
        linie "Acces la $u" $true "HTTP $($r.StatusCode)"
    } catch {
        linie "Acces la $u" $false "blocat sau fără internet ($($_.Exception.Message.Split([Environment]::NewLine)[0]))"
    }
}
foreach ($port in 80, 443, 8765, 5432) {
    $asc = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    linie "Portul $port" (-not $asc -or $port -in 80, 443) $(if ($asc) { "ocupat (procesul $($asc[0].OwningProcess))" } else { "liber" })
}
$fw = Get-NetFirewallProfile | ForEach-Object { "$($_.Name)=$(if ($_.Enabled) {'pornit'} else {'oprit'})" }
linie "Firewall" $true ($fw -join ", ")

Write-Host "`nTrimite-i lui Claude textul de mai sus (fără parole). Nimic nu s-a schimbat pe server.`n"
