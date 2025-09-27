#!/bin/bash
"""
Start the booking file polling service.
This script runs the Django management command to poll Google Drive folders.
"""

# Default polling interval (5 minutes for development)
INTERVAL=${BOOKING_POLL_INTERVAL:-300}

echo "Starting booking file polling service..."
echo "Polling interval: ${INTERVAL} seconds"
echo "Press Ctrl+C to stop"
echo ""

# Run the polling command
python manage.py poll_bookings --interval ${INTERVAL}