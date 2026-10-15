# ReHUB Disaster Recovery & Business Continuity Plan

**System:** ReHUB Residential Rehabilitation Management System  
**Jurisdiction:** Republic of Kenya (Data Protection Act 2019 / Kenya Health Act 2017)  
**Classification:** Institutional Standard Operating Procedure (SOP-ICT-004)  
**Status:** Institutional Ready  

---

## 1. Objectives & Recovery Targets

| Metric | Target | Rationale |
|---|---|---|
| **RPO (Recovery Point Objective)** | **≤ 1 Hour** | Inpatient clinical vital signs, medication rounds, crisis escalation notes, and financial billing must not lose more than 60 minutes of transaction data under any catastrophic failure. |
| **RTO (Recovery Time Objective)** | **≤ 2 Hours** | The residential facility operates 24/7. Critical eMAR, crisis monitoring, and nursing administration services must resume full operations within 120 minutes. |

---

## 2. Backup Strategy & Architecture

### 2.1 Database Backups (PostgreSQL)
1. **Full Database Backups (`pg_dump -Fc`):**
   - Executed automatically every night at 02:00 EAT via Celery Beat / scheduled cron using `scripts/backup.sh`.
   - Stored in compressed binary custom format retaining constraints, indexes, sequences, and metadata.
2. **Write-Ahead Logging (WAL) Archiving:**
   - WAL streaming enabled for continuous point-in-time recovery (PITR) guaranteeing the 1-hour RPO.
3. **Document & Media Backups:**
   - Client consent scans, referral letters, and lab toxicology reports are archived in `rehub_uploads_<timestamp>.tar.gz`.

### 2.2 Storage Hierarchy & Offsite Protection
- **Tier 1 (Local NVMe Storage):** `/var/backups/rehub/` — retained for 7 days for instant on-prem recovery.
- **Tier 2 (Offsite Cloud Storage):** Encrypted secondary copy synced to dedicated sovereign S3-compatible cold bucket located within Kenya/East Africa region complying with ODPC cross-border transfer restrictions.
- **Encryption:** All offsite backups are encrypted using AES-256-CBC (`openssl enc -aes-256-cbc -pbkdf2`). Encryption keys are maintained in an offline hardware security key held by the ICT Director and Medical Director.

### 2.3 Retention Policy
- Daily backups: Retained for 30 days.
- Weekly backups: Retained for 12 weeks.
- Monthly backups: Retained for 7 years (aligned with Kenya Companies Act and Health Act requirements).

---

## 3. Restoration Procedure

### 3.1 Scenario A: Automated DR Verification Test
Executed bi-weekly on a dedicated isolated environment to verify backup integrity:
```bash
# Run automated restore smoke test
./scripts/restore_test.sh /var/backups/rehub/20261012_000000Z/rehub_db_20261012_000000Z.dump
```
The script performs:
1. Creation of an isolated ephemeral database (`rehub_restore_test_<timestamp>`).
2. Full `pg_restore` with table/index reconstruction.
3. Validation of the current Alembic schema revision (`alembic_version`).
4. Row count checks across `users`, `facilities`, `clients`, `admissions`, `finance_chart_of_accounts`, and `audit_events`.
5. Automatic financial balance validation (`SELECT SUM(debit) == SUM(credit)`).
6. Automatic destruction of ephemeral test database.

### 3.2 Scenario B: Full Bare-Metal Production Recovery
In the event of physical host destruction or complete data loss:
1. **Provision New Host:** Initialize Ubuntu 22.04 LTS host with Docker & Docker Compose.
2. **Fetch Latest Verified Backup:** Download encrypted archive from offsite storage.
3. **Decrypt Backup:**
   ```bash
   openssl enc -d -aes-256-cbc -pbkdf2 -in rehub_backup_YYYYMMDD.tar.gz.enc -out rehub_backup_YYYYMMDD.tar.gz
   tar -xzf rehub_backup_YYYYMMDD.tar.gz
   ```
4. **Initialize PostgreSQL Container:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres
   ```
5. **Restore Database:**
   ```bash
   docker compose -f docker-compose.prod.yml exec -T postgres pg_restore \
     -U ars -d ars_rms --clean --if-exists < rehub_db_YYYYMMDD.dump
   ```
6. **Launch Full Application Stack:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
7. **Verify Service Health:**
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

---

## 4. Responsible Roles & Escalation Matrix

| Role | Primary Responsibility | Contact Trigger |
|---|---|---|
| **ICT Systems Administrator** | Executes daily backups, monitors storage thresholds, triggers restore verification. | Backup failure, storage warning (>80%). |
| **Data Protection Officer (DPO)** | Ensures ODPC statutory adherence, oversees encryption standards, logs disaster declarations. | Any incident involving potential data loss or corruption. |
| **Medical Director** | Approves clinical failover protocols, authorizes paper chart downtime procedure. | Downtime exceeding 30 minutes during active clinic hours. |
| **Lead Developer / DevOps** | Validates migration schema consistency, investigates database integrity anomalies. | Schema drift or restoration failure. |

---

## 5. Verification Schedule & Audit Records

- **Daily:** Backup task status audited in Celery job monitor (`/admin/jobs`).
- **Bi-Weekly:** Automated restore script executed against latest dump; results logged in `audit_events`.
- **Quarterly:** Simulated institutional disaster drill with simulated DNS failover and Medical Director sign-off.
