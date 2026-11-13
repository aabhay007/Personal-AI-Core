# ==============================================================================
# Personal AI Core - Production Database & Document Storage Restore (PowerShell)
# ==============================================================================
param (
    [Parameter(Mandatory=$true)]
    [string]$DbBackupFile,
    [string]$StorageBackupFile,
    [string]$DbContainer = "personal_ai_postgres",
    [string]$DbName = "personal_ai_core",
    [string]$DbUser = "postgres",
    [string]$StoragePath = "../backend/storage"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $DbBackupFile)) {
    Write-Error "Backup file not found: $DbBackupFile"
    exit 1
}

Write-Host "==> Restoring Personal AI Core from $DbBackupFile..." -ForegroundColor Cyan

# 1. Restore Database
Write-Host "--> Restoring database '$DbName'..." -ForegroundColor Gray
Get-Content $DbBackupFile | docker exec -i $DbContainer psql -U $DbUser -d $DbName
Write-Host "    Database restored successfully." -ForegroundColor Green

# 2. Restore Storage
if ($StorageBackupFile -and (Test-Path $StorageBackupFile)) {
    Write-Host "--> Restoring storage to '$StoragePath'..." -ForegroundColor Gray
    if (!(Test-Path $StoragePath)) {
        New-Item -ItemType Directory -Path $StoragePath | Out-Null
    }
    Expand-Archive -Path $StorageBackupFile -DestinationPath $StoragePath -Force
    Write-Host "    Storage restored successfully." -ForegroundColor Green
}

Write-Host "==> Recovery complete!" -ForegroundColor Cyan
