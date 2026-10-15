#!/usr/bin/env bash
# ==============================================================================
# ReHUB Production Automated Backup Script
# Healthcare & Institutional Data Protection (KDPA 2019 / Kenya Health Act)
# ==============================================================================
# Strict mode: fail on error, unbound variables, or pipe failure
set -euo pipefail

# Configuration via environment variables (NEVER hardcode secrets)
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-ars}"
PGDATABASE="${PGDATABASE:-ars_rms}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/rehub}"
UPLOADS_DIR="${UPLOADS_DIR:-/var/lib/rehub/uploads}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENCRYPTION_KEY="${BACKUP_PASSPHRASE:-}"

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_SUBDIR="${BACKUP_DIR}/${TIMESTAMP}"
mkdir -p "${BACKUP_SUBDIR}"

echo "[$(date -u)] Starting ReHUB Production Backup: ${TIMESTAMP}"

# 1. PostgreSQL Full Database Dump (Custom Compressed Binary Format)
DB_BACKUP_FILE="${BACKUP_SUBDIR}/rehub_db_${TIMESTAMP}.dump"
echo "[$(date -u)] Dumping PostgreSQL database '${PGDATABASE}' from ${PGHOST}:${PGPORT}..."
pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    -Fc --no-owner --no-privileges -f "${DB_BACKUP_FILE}"

# 2. Uploaded Institutional Documents Archive
DOCS_BACKUP_FILE="${BACKUP_SUBDIR}/rehub_uploads_${TIMESTAMP}.tar.gz"
if [ -d "${UPLOADS_DIR}" ]; then
    echo "[$(date -u)] Archiving uploaded documents from ${UPLOADS_DIR}..."
    tar -czf "${DOCS_BACKUP_FILE}" -C "$(dirname "${UPLOADS_DIR}")" "$(basename "${UPLOADS_DIR}")"
else
    echo "[$(date -u)] Notice: Uploads directory not found, skipping document archive."
fi

# 3. Generate SHA-256 Integrity Checksums
echo "[$(date -u)] Generating SHA-256 checksums..."
cd "${BACKUP_SUBDIR}"
sha256sum * > SHA256SUMS.txt
cd - > /dev/null

# 4. Optional AES-256 Encryption
if [ -n "${ENCRYPTION_KEY}" ]; then
    echo "[$(date -u)] Encrypting backup archive with AES-256-CBC..."
    ARCHIVE_FILE="${BACKUP_DIR}/rehub_backup_${TIMESTAMP}.tar.gz"
    tar -czf - -C "${BACKUP_DIR}" "${TIMESTAMP}" | \
        openssl enc -aes-256-cbc -salt -pbkdf2 -pass "env:BACKUP_PASSPHRASE" -out "${ARCHIVE_FILE}.enc"
    rm -rf "${BACKUP_SUBDIR}"
    echo "[$(date -u)] Encrypted archive created: ${ARCHIVE_FILE}.enc"
else
    echo "[$(date -u)] Notice: BACKUP_PASSPHRASE not set. Backup stored unencrypted at ${BACKUP_SUBDIR}"
fi

# 5. Backup Retention Rotation (Prune older than RETENTION_DAYS)
echo "[$(date -u)] Applying backup retention policy (${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true
find "${BACKUP_DIR}" -maxdepth 1 -name "rehub_backup_*.enc" -mtime "+${RETENTION_DAYS}" -exec rm -f {} + 2>/dev/null || true

echo "[$(date -u)] ReHUB Backup completed successfully."
exit 0
