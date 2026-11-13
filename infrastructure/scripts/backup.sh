#!/bin/bash
# ==============================================================================
# Personal AI Core - Production Database & Document Storage Backup Script
# ==============================================================================
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER="${DB_CONTAINER:-personal_ai_postgres}"
DB_NAME="${DB_NAME:-personal_ai_core}"
DB_USER="${DB_USER:-postgres}"
STORAGE_PATH="${STORAGE_PATH:-../backend/storage}"

mkdir -p "${BACKUP_DIR}"

echo "==> Starting Personal AI Core backup at ${TIMESTAMP}..."

# 1. PostgreSQL Database Dump (with pgvector schema and tables)
DB_BACKUP_FILE="${BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"
echo "--> Dumping PostgreSQL database '${DB_NAME}'..."
docker exec -t "${DB_CONTAINER}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${DB_BACKUP_FILE}"
echo "    Database backup saved: ${DB_BACKUP_FILE}"

# 2. Document storage backup
if [ -d "${STORAGE_PATH}" ]; then
    STORAGE_BACKUP_FILE="${BACKUP_DIR}/storage_${TIMESTAMP}.tar.gz"
    echo "--> Archiving document storage '${STORAGE_PATH}'..."
    tar -czf "${STORAGE_BACKUP_FILE}" -C "${STORAGE_PATH}" .
    echo "    Storage backup saved: ${STORAGE_BACKUP_FILE}"
fi

echo "==> Backup completed successfully at $(date)!"
