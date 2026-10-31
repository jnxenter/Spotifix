#requires -Version 5.1
<#
.SYNOPSIS
    Actualiza SonicPush STA a la ultima version publicada en jnxenter/Spotifix.

.DESCRIPTION
    Las instalaciones viejas tenian el actualizador apuntando a
    rogelioguzmantiti-hub/Spotifix. Este script hace la migracion UNA sola vez:
    descarga los archivos de jnxenter/Spotifix y los copia en la carpeta de la
    app (pidiendo permisos de administrador si esta en Program Files).
    Despues de esto, el boton "Check for Updates" de la app ya usa jonex.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Actualizar-SonicPush.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Actualizar-SonicPush.ps1 -AppDir "D:\Apps\SonicPush STA\resources\app" -NoRestart
#>
param(
    [string]$Repo = 'jnxenter/Spotifix',
    [string]$Branch = 'main',
    [string]$AppDir = '',
    [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Files = @('api.py', 'renderer.js', 'index.html', 'login.html', 'main.js', 'preload.js', 'package.json')
$ExeName = 'SonicPush STA.exe'

function Find-AppDir {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'SonicPush STA\resources\app'),
        (Join-Path ${env:ProgramFiles(x86)} 'SonicPush STA\resources\app'),
        (Join-Path $env:LOCALAPPDATA 'Programs\SonicPush STA\resources\app'),
        (Join-Path $env:LOCALAPPDATA 'SonicPush STA\resources\app')
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path (Join-Path $c 'api.py'))) { return $c }
    }
    # Fallback: buscar api.py debajo de las carpetas tipicas
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))) {
        if (-not $base -or -not (Test-Path $base)) { continue }
        $hit = Get-ChildItem -Path $base -Filter 'api.py' -Recurse -Depth 4 -ErrorAction SilentlyContinue |
            Where-Object { $_.DirectoryName -match 'resources\\app$' } | Select-Object -First 1
        if ($hit) { return $hit.DirectoryName }
    }
    return $null
}

function Is-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-ElevatedSelf {
    Write-Host 'Se necesitan permisos de administrador (UAC)...' -ForegroundColor Yellow
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"",
                 '-Repo', $Repo, '-Branch', $Branch, '-AppDir', "`"$AppDir`"")
    if ($NoRestart) { $argList += '-NoRestart' }
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -ArgumentList $argList
    exit $LASTEXITCODE
}

if (-not $AppDir) { $AppDir = Find-AppDir }
if (-not $AppDir -or -not (Test-Path (Join-Path $AppDir 'api.py'))) {
    Write-Host 'No encontre la carpeta de la app (resources\app con api.py).' -ForegroundColor Red
    Write-Host 'Pasa la ruta a mano, por ejemplo:'
    Write-Host '  -AppDir "C:\Program Files\SonicPush STA\resources\app"'
    exit 1
}
$AppDir = (Resolve-Path $AppDir).Path
Write-Host "Carpeta de la app: $AppDir"

$current = (Select-String -Path (Join-Path $AppDir 'api.py') -Pattern '^Bot_version\s*=\s*"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value
$currentRepo = (Select-String -Path (Join-Path $AppDir 'api.py') -Pattern '^GITHUB_REPO\s*=\s*"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value
Write-Host "Version instalada: $current  (repositorio configurado: $currentRepo)"

# Version remota (sin usar la API: /releases/latest redirige al tag)
$remote = ''
try {
    $r = Invoke-WebRequest -Uri "https://github.com/$Repo/releases/latest" -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
    $loc = $r.Headers.Location
} catch { $loc = $_.Exception.Response.Headers.Location }
if ($loc -match '/tag/v?([0-9][0-9\.]*)') { $remote = $Matches[1] }
if ($remote) { Write-Host "Version publicada:  $remote  ($Repo)" }

function ConvertTo-VerTuple([string]$v) {
    $parts = ($v -split '\.') | ForEach-Object { if ($_ -match '^\d+$') { [int]$_ } else { 0 } }
    while ($parts.Count -lt 4) { $parts += 0 }
    return ($parts[0..3] -join ',')
}

if ($remote -and ((ConvertTo-VerTuple $remote) -eq (ConvertTo-VerTuple $current))) {
    Write-Host 'Ya esta en la ultima version. Nada que hacer.' -ForegroundColor Green
    exit 0
}

if (-not (Is-Admin)) { Invoke-ElevatedSelf }

$backup = Join-Path $env:TEMP ("sonicpush_backup_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $backup | Out-Null

# Intentar primero el ZIP del tag (mas rapido y consistente)
$zipOk = $false
$zipRoot = $null
$tag = if ($remote) { "v$remote" } else { $null }
if ($tag) {
    try {
        $zipPath = Join-Path $env:TEMP ("sonicpush_$tag.zip")
        Write-Host "Descargando $Repo $tag ..."
        curl.exe -sL --max-time 300 -o $zipPath "https://codeload.github.com/$Repo/zip/refs/tags/$tag"
        if ((Test-Path $zipPath) -and (Get-Item $zipPath).Length -gt 100000) {
            $extract = Join-Path $env:TEMP ("sonicpush_$tag")
            Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue
            Expand-Archive -Path $zipPath -DestinationPath $extract -Force
            $zipRoot = (Get-ChildItem $extract -Directory | Select-Object -First 1).FullName
            $zipOk = $true
            Write-Host "ZIP listo: $zipRoot"
        }
    } catch { Write-Host "ZIP fallo, se usara descarga archivo por archivo: $($_.Exception.Message)" -ForegroundColor Yellow }
}

foreach ($f in $Files) {
    $dest = Join-Path $AppDir $f
    if (Test-Path $dest) { Copy-Item $dest (Join-Path $backup $f) -Force }
    $ok = $false
    if ($zipOk) {
        $src = Join-Path $zipRoot ($f -replace '/', '\')
        if (Test-Path $src) { Copy-Item $src $dest -Force; $ok = $true }
    }
    if (-not $ok) {
        foreach ($url in @(
            "https://raw.githubusercontent.com/$Repo/$Branch/$f",
            "https://github.com/$Repo/raw/$Branch/$f")) {
            try {
                Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -TimeoutSec 90
                if ((Get-Item $dest).Length -gt 0) { $ok = $true; break }
            } catch { }
        }
    }
    if ($ok) { Write-Host ("  OK  " + $f) -ForegroundColor Green }
    else { Write-Host ("  FALLO  " + $f) -ForegroundColor Red }
}

$newVer = (Select-String -Path (Join-Path $AppDir 'api.py') -Pattern '^Bot_version\s*=\s*"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value
$newRepo = (Select-String -Path (Join-Path $AppDir 'api.py') -Pattern '^GITHUB_REPO\s*=\s*"([^"]+)"' |
    Select-Object -First 1).Matches.Groups[1].Value
Write-Host ""
Write-Host "Version instalada ahora: $newVer  (actualizador apunta a: $newRepo)" -ForegroundColor Cyan
Write-Host "Respaldo de los archivos anteriores: $backup"

if (-not $NoRestart) {
    $exe = Join-Path (Split-Path (Split-Path $AppDir -Parent) -Parent) $ExeName
    Write-Host "Reiniciando la app..."
    Get-Process -Name 'SonicPush STA' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process -Name 'api' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    if (Test-Path $exe) { Start-Process -FilePath $exe }
    else { Write-Host "No encontre el ejecutable en $exe; abrelo a mano." -ForegroundColor Yellow }
}
