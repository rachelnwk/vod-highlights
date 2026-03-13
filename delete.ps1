$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$AppName = "vod-highlights-backend"
$Region = "us-east-2"
$Platform = "Node.js"

Write-Host ""
Write-Host "1. initializing EB"
& eb init $AppName --platform $Platform --region $Region

Write-Host ""
Write-Host "2. deleting app"

Get-ChildItem -Path $PSScriptRoot -Filter "*.zip" -File -ErrorAction SilentlyContinue | Remove-Item -Force
& eb terminate --all --force $AppName
