# ==============================================================================
# Personal AI Core - Production Database & Document Storage Backup (PowerShell)
# ==============================================================================
param (
    [string]$BackupDir = "./backups",
    [string]$DbContainer = "personal_ai_postgres",
    [string]$DbName = "personal_ai_core",
    [string]$DbUser = "postgres",
    [string]$StoragePath = "../backend/storage"
)

$ErrorActionPreference = "Stop"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (!(Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Write-Host "==> Starting Personal AI Core backup at $Timestamp..." -ForegroundColor Cyan

# 1. PostgreSQL Database Dump
$DbBackupFile = Join-Path $BackupDir "db_${DbName}_${Timestamp}.sql"
Write-Host "--> Dumping PostgreSQL database '$DbName'..." -ForegroundColor Gray
docker exec -i $DbContainer pg_dump -U $DbUser $DbName > $DbBackupFile
Write-Host "    Database backup saved: $DbBackupFile" -ForegroundColor Green

# 2. Document storage backup
if (Test-Path $StoragePath) {
    $StorageBackupFile = Join-Path $BackupDir "storage_${Timestamp}.zip"
    Write-Host "--> Archiving document storage '$StoragePath'..." -ForegroundColor Gray
    Compress-Archive -Path "$StoragePath/*" -DestinationPath $StorageBackupFile -Force
    Write-Host "    Storage backup saved: $StorageBackupFile" -ForegroundColor Green
}

Write-Host "==> Backup completed successfully!" -ForegroundColor Cyan
