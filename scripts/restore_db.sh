#!/bin/bash
# restore_db.sh - Database restore script

set -e

# Check if backup file is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/backup_20240115_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables
if [ -f .env.prod ]; then
    export $(grep -v '^#' .env.prod | xargs)
fi

# Confirm restoration
echo "WARNING: This will restore the database from: $BACKUP_FILE"
echo "All current data will be replaced!"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restoration cancelled."
    exit 0
fi

echo "Starting database restoration..."

# Decompress if needed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    TEMP_FILE=$(mktemp)
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    RESTORE_FILE="$TEMP_FILE"
else
    RESTORE_FILE="$BACKUP_FILE"
fi

# Perform restoration
if command -v docker &> /dev/null; then
    # If running with Docker
    docker compose -f docker-compose.prod.yml exec -T db psql \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        < "$RESTORE_FILE"
else
    # If running locally
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h localhost \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        < "$RESTORE_FILE"
fi

# Clean up temp file if created
if [ ! -z "$TEMP_FILE" ]; then
    rm "$TEMP_FILE"
fi

echo "Database restoration completed successfully!"
echo "You may need to restart your application for changes to take effect."