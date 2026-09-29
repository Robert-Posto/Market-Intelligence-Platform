# Pe SERVER, ca administrator: IIS ca poartă de intrare (HTTPS + cont de domeniu).
# Înainte: instalează URL Rewrite și Application Request Routing 3.0 (installere
# offline de la Microsoft), altfel regula din web.config nu are ce rula.
#   .\deploy\instaleaza_iis.ps1 -Dns mcc.libra.local -Radacina D:\mcc
param(
    [Parameter(Mandatory = $true)] [string]$Dns,
    [string]$Radacina = "D:\mcc",
    [string]$Site = "MCC"
)
$ErrorActionPreference = "Stop"

Install-WindowsFeature Web-Server, Web-Windows-Auth, Web-Url-Auth, Web-Mgmt-Console | Out-Null
Import-Module WebAdministration

# ARR: proxy activat la nivel de server (fără el, Rewrite spre 127.0.0.1 dă 404)
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Filter "system.webServer/proxy" -Name enabled -Value $true
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Filter "system.webServer/proxy" -Name timeout -Value "00:03:00"

# site-ul: un folder care conține doar web.config (aplicația rulează separat, ca serviciu)
$www = Join-Path $Radacina "iis"
New-Item -ItemType Directory -Force $www | Out-Null
Copy-Item (Join-Path $PSScriptRoot "web.config") $www -Force
if (-not (Get-Website -Name $Site -ErrorAction SilentlyContinue)) {
    New-Website -Name $Site -PhysicalPath $www -HostHeader $Dns -Port 80 | Out-Null
}
if (-not (Get-WebBinding -Name $Site -Protocol https)) {
    New-WebBinding -Name $Site -Protocol https -Port 443 -HostHeader $Dns -SslFlags 1
}

# doar Windows Authentication (Kerberos/NTLM), fără acces anonim
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Location $Site -Filter "system.webServer/security/authentication/anonymousAuthentication" -Name enabled -Value $false
Set-WebConfigurationProperty -PSPath "MACHINE/WEBROOT/APPHOST" -Location $Site -Filter "system.webServer/security/authentication/windowsAuthentication" -Name enabled -Value $true

Write-Host "Site-ul $Site e creat pentru $Dns."
Write-Host "Mai rămân: certificatul HTTPS (IIS Manager > $Site > Bindings > https > SSL certificate)"
Write-Host "și grupul AD din $www\web.config (DOMENIU\Grup-MCC)."
