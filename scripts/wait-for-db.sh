#!/bin/sh
# wait-for-db.sh

set -e

echo "Waiting for PostgreSQL to become available..."

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done

echo "PostgreSQL is available"