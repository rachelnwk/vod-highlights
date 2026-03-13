$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppName = "vod-highlights-backend"
$EnvName = "vod-highlights-backend-env"
$Region = "us-east-2"
$Platform = "Node.js"
$ZipFile = "backend.zip"
$AppDir = "backend"
$UniqueId = Get-Date -Format "yyyyMMdd-HHmmss"
$Version = "$UniqueId-$ZipFile"

function Test-IsExcluded {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "\\", "/"

    return (
        $normalized -like "node_modules/*" -or
        $normalized -like "*.log" -or
        $normalized -like "npm-debug.log*" -or
        $normalized -eq ".DS_Store" -or
        $normalized -like ".git/*" -or
        $normalized -eq ".env" -or
        $normalized -like ".env.*"
    )
}

function New-BackendArchive {
    param([string]$ArchivePath)

    $backendDir = Join-Path $PSScriptRoot $AppDir
    $stagingDir = Join-Path ([System.IO.Path]::GetTempPath()) ("vod-highlights-backend-" + [guid]::NewGuid().ToString())

    if (Test-Path $ArchivePath) {
        Remove-Item $ArchivePath -Force
    }

    New-Item -ItemType Directory -Path $stagingDir | Out-Null

    try {
        Get-ChildItem -Path $backendDir -Recurse -File -Force | ForEach-Object {
            $relativePath = $_.FullName.Substring($backendDir.Length).TrimStart('\', '/')
            if (Test-IsExcluded $relativePath) {
                return
            }

            $destinationPath = Join-Path $stagingDir $relativePath
            $destinationDir = Split-Path $destinationPath -Parent
            if (-not (Test-Path $destinationDir)) {
                New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
            }

            Copy-Item $_.FullName $destinationPath
        }

        Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $ArchivePath -Force
    }
    finally {
        if (Test-Path $stagingDir) {
            Remove-Item $stagingDir -Recurse -Force
        }
    }
}

Write-Host ""
Write-Host "1. initializing EB"
& eb init $AppName --platform $Platform --region $Region

Write-Host ""
Write-Host "2. packaging app"
$archivePath = Join-Path $PSScriptRoot $Version
New-BackendArchive -ArchivePath $archivePath

Write-Host ""
Write-Host "3. Deploying app to EB..."
& eb deploy $EnvName --archive $archivePath --region $Region

Write-Host ""
Write-Host "Done! You can use 'eb status' to check status of web service."
Write-Host ""
