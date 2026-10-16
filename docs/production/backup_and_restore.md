# ProctorAI — Database Backup & Disaster Recovery Guide

This document describes the backup, validation, and disaster recovery procedures for **ProctorAI** production databases (PostgreSQL 15+) and development environments.

---

## 1. Backup Strategy Overview

| Tier | Backup Type | Frequency | Retention | Target Storage |
| :--- | :--- | :--- | :--- | :--- |
| **Continuous** | WAL (Write-Ahead Log) Archiving | Realtime (16MB segments) | 14 Days | Offsite Object Storage (S3 / GCS) |
| **Daily** | Full Logical Dump (`pg_dump`) | Every day at 02:00 UTC | 30 Days | Encrypted Cloud Bucket (`AES-256`) |
| **Weekly** | Full System Snapshot | Weekly (Sundays 03:00 UTC) | 90 Days | Air-gapped Cold Storage |

---

## 2. Automated Daily Logical Backup Script

Create `/usr/local/bin/proctorai-backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/proctorai"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/proctorai_db_${TIMESTAMP}.dump"
LOG_FILE="/var/log/proctorai/backup.log"
RETENTION_DAYS=30

# Database credentials sourced from secure environment file
source /etc/proctorai/proctorai.env

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u)] Starting ProctorAI database backup..." >> "${LOG_FILE}"

# Execute custom-format compressed backup with integrity checksum
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_SERVER}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -F c \
    -b \
    -v \
    -f "${BACKUP_FILE}" 2>> "${LOG_FILE}"

# Generate SHA-256 Checksum
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"

# Verify backup archive integrity
PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore --list "${BACKUP_FILE}" > /dev/null

echo "[$(date -u)] Backup successful: ${BACKUP_FILE} (Size: $(du -h "${BACKUP_FILE}" | cut -f1))" >> "${LOG_FILE}"

# Clean up backups older than retention policy
find "${BACKUP_DIR}" -name "proctorai_db_*.dump*" -mtime +"${RETENTION_DAYS}" -delete
```

Set permissions:
```bash
chmod 700 /usr/local/bin/proctorai-backup.sh
chown root:root /usr/local/bin/proctorai-backup.sh
```

### Cron Schedule (`/etc/cron.d/proctorai-backup`)

```cron
0 2 * * * root /usr/local/bin/proctorai-backup.sh >/dev/null 2>&1
```

---

## 3. Disaster Recovery & Database Restoration

### Step 1: Pre-flight Verification
Verify the SHA-256 checksum of the target backup archive before restoration:

```bash
sha256sum -c proctorai_db_20261017_020000Z.dump.sha256
```

### Step 2: Stop Backend Traffic
Drain active web traffic to prevent inconsistent writes during restoration:

```bash
systemctl stop proctorai-backend
```

### Step 3: Create Fresh Database (or Terminate Active Connections)
If restoring into an existing database instance, terminate lingering connection sessions:

```sql
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'proctorai_db' AND pid <> pg_backend_pid();
```

Drop and recreate the empty target database:

```bash
PGPASSWORD="${POSTGRES_PASSWORD}" dropdb -h "${POSTGRES_SERVER}" -U "${POSTGRES_USER}" proctorai_db
PGPASSWORD="${POSTGRES_PASSWORD}" createdb -h "${POSTGRES_SERVER}" -U "${POSTGRES_USER}" -O "${POSTGRES_USER}" proctorai_db
```

### Step 4: Restore Data using `pg_restore`

```bash
PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
    -h "${POSTGRES_SERVER}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d proctorai_db \
    -v \
    --no-owner \
    --role="${POSTGRES_USER}" \
    proctorai_db_20261017_020000Z.dump
```

### Step 5: Run Alembic Migration Check
Ensure all migrations are synchronized with active code:

```bash
cd /opt/proctorai/backend
.venv/bin/alembic upgrade head
```

### Step 6: Verify Service Health & Resume Traffic
Start the backend service and test readiness probe:

```bash
systemctl start proctorai-backend
curl -f http://127.0.0.1:8000/health/ready
```

---

## 4. SQLite Development Backup & Restore

For local development or staging instances utilizing SQLite (`intellitest.db`):

```bash
# Safe Online Backup (locks database safely using sqlite3 online backup API)
sqlite3 intellitest.db ".backup 'intellitest_backup_$(date +%Y%m%d).db'"

# Restore from backup
cp intellitest_backup_20261017.db intellitest.db
```
