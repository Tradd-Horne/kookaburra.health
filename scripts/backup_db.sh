#!/bin/bash
# backup_db.sh - Database backup script

set -e

# Load environment variables
if [ -f .env.prod ]; then
    export $(grep -v '^#' .env.prod | xargs)
fi

# Create backup directory if it doesn't exist
BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

# Perform backup
echo "Starting database backup..."

if command -v docker &> /dev/null; then
    # If running with Docker
    docker compose -f docker-compose.prod.yml exec -T db pg_dump \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --no-owner \
        --no-privileges \
        > "$BACKUP_FILE"
else
    # If running locally
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h localhost \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --no-owner \
        --no-privileges \
        > "$BACKUP_FILE"
fi

# Compress the backup
gzip "$BACKUP_FILE"

echo "Backup completed: ${BACKUP_FILE}.gz"

# Optional: Remove old backups (keep last 7 days)
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +7 -delete

echo "Old backups cleaned up (kept last 7 days)"