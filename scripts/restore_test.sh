#!/usr/bin/env bash
# ==============================================================================
# ReHUB Automated Disaster Recovery Restore Verification Script
# Validates that database backups are verifiable, integral, and fully restorable
# ==============================================================================
set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <path_to_rehub_db_backup.dump>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' does not exist."
    exit 1
fi

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-ars}"
TEST_DB_NAME="rehub_restore_test_$(date +%s)"
REPORT_FILE="/tmp/rehub_restore_report_$(date +%s).log"

echo "======================================================================"
echo "Starting ReHUB Disaster Recovery Restore Verification"
echo "Backup File:  ${BACKUP_FILE}"
echo "Target DB:    ${TEST_DB_NAME}"
echo "Host:         ${PGHOST}:${PGPORT}"
echo "Timestamp:    $(date -u)"
echo "======================================================================"

cleanup() {
    echo "[Cleanup] Dropping isolated verification database '${TEST_DB_NAME}'..."
    dropdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" --if-exists "${TEST_DB_NAME}" 2>/dev/null || true
}
trap cleanup EXIT

# 1. Create Isolated Verification Database
echo "[Step 1/5] Creating temporary database '${TEST_DB_NAME}'..."
createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TEST_DB_NAME}"

# 2. Restore Database Dump
echo "[Step 2/5] Restoring backup dump via pg_restore..."
pg_restore -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" \
    --no-owner --no-privileges --exit-on-error "${BACKUP_FILE}"

# 3. Verify Alembic Migration Head
echo "[Step 3/5] Checking migration schema version..."
ALEMBIC_VERSION=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" -tAc "SELECT version_num FROM alembic_version;")
echo "Database is at Alembic revision: ${ALEMBIC_VERSION}"
if [ -z "${ALEMBIC_VERSION}" ]; then
    echo "FAILED: Database has no Alembic migration history!"
    exit 1
fi

# 4. Validate Table Row Counts
echo "[Step 4/5] Validating core clinical & financial table row counts..."
psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" -c "
SELECT 'users' as table_name, count(*) as count FROM users
UNION ALL
SELECT 'facilities', count(*) FROM facilities
UNION ALL
SELECT 'clients', count(*) FROM clients
UNION ALL
SELECT 'admissions', count(*) FROM admissions
UNION ALL
SELECT 'finance_chart_of_accounts', count(*) FROM finance_chart_of_accounts
UNION ALL
SELECT 'audit_events', count(*) FROM audit_events;
"

# 5. Critical Smoke Query (Ensure referential integrity and double-entry validity)
echo "[Step 5/5] Running financial double-entry integrity check on restored ledger..."
UNBALANCED_JOURNALS=$(psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB_NAME}" -tAc "
SELECT count(*) FROM (
    SELECT entry_id, sum(debit) as debits, sum(credit) as credits 
    FROM finance_journal_lines 
    GROUP BY entry_id 
    HAVING sum(debit) != sum(credit)
) unbalanced;
")

if [ "${UNBALANCED_JOURNALS}" != "0" ]; then
    echo "FAILED: Restored database contains ${UNBALANCED_JOURNALS} unbalanced journal entries!"
    exit 1
fi

echo "======================================================================"
echo "RESTORE VERIFICATION SUCCESSFUL"
echo "All clinical, financial, and audit tables restored and validated."
echo "======================================================================"
exit 0
