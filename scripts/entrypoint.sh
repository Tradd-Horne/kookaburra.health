#!/bin/sh
# entrypoint.sh

set -e

# Parse DATABASE_URL to get host and port
export POSTGRES_HOST=$(echo "$DATABASE_URL" | sed -E 's/.*@([^:]+):.*/\1/')
export POSTGRES_PORT=$(echo "$DATABASE_URL" | sed -E 's/.*:([0-9]+)\/.*/\1/')

# Wait for database
/app/scripts/wait-for-db.sh

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Execute the main command
exec "$@"