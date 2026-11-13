#!/bin/bash
# ==============================================================================
# Personal AI Core - Production Database & Document Storage Restore Script
# ==============================================================================
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <path_to_db_dump.sql.gz> [path_to_storage.tar.gz]"
    exit 1
fi

DB_BACKUP_FILE="$1"
STORAGE_BACKUP_FILE="$2"
DB_CONTAINER="${DB_CONTAINER:-personal_ai_postgres}"
DB_NAME="${DB_NAME:-personal_ai_core}"
DB_USER="${DB_USER:-postgres}"
STORAGE_PATH="${STORAGE_PATH:-../backend/storage}"

echo "==> Restoring Personal AI Core from '${DB_BACKUP_FILE}'..."

# 1. Restore Database
echo "--> Restoring database '${DB_NAME}'..."
gunzip -c "${DB_BACKUP_FILE}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}"
echo "    Database restored successfully."

# 2. Restore Storage
if [ -n "${STORAGE_BACKUP_FILE}" ] && [ -f "${STORAGE_BACKUP_FILE}" ]; then
    echo "--> Restoring storage to '${STORAGE_PATH}'..."
    mkdir -p "${STORAGE_PATH}"
    tar -xzf "${STORAGE_BACKUP_FILE}" -C "${STORAGE_PATH}"
    echo "    Storage restored successfully."
fi

echo "==> Recovery complete!"
