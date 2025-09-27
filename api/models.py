"""
API models for Google Drive integration.
"""
from django.contrib.auth import get_user_model
from django.db import models
from decimal import Decimal
import hashlib
import json

User = get_user_model()


class GoogleDriveFolder(models.Model):
    """
    Model to store Google Drive folder information and access details.
    """
    folder_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Google Drive folder ID"
    )
    folder_name = models.CharField(
        max_length=255,
        help_text="Google Drive folder name"
    )
    owner_email = models.EmailField(
        help_text="Email of the folder owner"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='google_drive_folders',
        help_text="User who has access to this folder"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_validated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this folder was validated"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this folder is actively being monitored"
    )

    class Meta:
        db_table = 'api_google_drive_folders'
        verbose_name = 'Google Drive Folder'
        verbose_name_plural = 'Google Drive Folders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.folder_name} ({self.folder_id})"


class GoogleDriveWatchConfig(models.Model):
    """
    Model to store Google Drive watch configuration for folders.
    """
    NOTIFICATION_TYPES = [
        ('file_added', 'File Added'),
        ('file_removed', 'File Removed'),
        ('file_modified', 'File Modified'),
        ('all', 'All Changes'),
    ]

    folder = models.ForeignKey(
        GoogleDriveFolder,
        on_delete=models.CASCADE,
        related_name='watch_configs',
        help_text="Google Drive folder being watched"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='drive_watch_configs',
        help_text="User who created this watch configuration"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='all',
        help_text="Type of changes to watch for"
    )
    webhook_url = models.URLField(
        blank=True,
        null=True,
        help_text="Webhook URL to send notifications to"
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text="Whether to send email notifications"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this watch configuration is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Google Drive API specific fields (for future implementation)
    resource_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Google Drive API resource ID for the watch"
    )
    expiration = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the watch expires"
    )

    class Meta:
        db_table = 'api_google_drive_watch_configs'
        verbose_name = 'Google Drive Watch Configuration'
        verbose_name_plural = 'Google Drive Watch Configurations'
        ordering = ['-created_at']
        unique_together = ['folder', 'user']

    def __str__(self):
        return f"Watch for {self.folder.folder_name} by {self.user.username}"


class IngestionRun(models.Model):
    """
    Model to track ingestion runs for audit and idempotency.
    """
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]

    folder = models.ForeignKey(
        GoogleDriveFolder,
        on_delete=models.CASCADE,
        related_name='ingestion_runs',
        help_text="Folder being processed"
    )
    file_id = models.CharField(
        max_length=255,
        help_text="Google Drive file ID"
    )
    filename = models.CharField(
        max_length=500,
        help_text="Original filename"
    )
    file_created_time = models.DateTimeField(
        help_text="When the file was created in Google Drive"
    )
    file_modified_time = models.DateTimeField(
        help_text="When the file was last modified in Google Drive"
    )
    data_time = models.DateTimeField(
        help_text="Extracted data timestamp (from filename or file creation)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Processing metadata
    sheet_names = models.JSONField(
        default=list,
        help_text="Names of sheets processed"
    )
    rows_processed = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_ignored = models.PositiveIntegerField(default=0)
    rows_quarantined = models.PositiveIntegerField(default=0)
    conflicts_detected = models.PositiveIntegerField(default=0)
    
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if processing failed"
    )

    class Meta:
        db_table = 'api_ingestion_runs'
        verbose_name = 'Ingestion Run'
        verbose_name_plural = 'Ingestion Runs'
        ordering = ['-started_at']
        unique_together = ['folder', 'file_id']

    def __str__(self):
        return f"Ingestion {self.id}: {self.filename} ({self.status})"


class ProcessedFile(models.Model):
    """
    Model to track processed files for idempotency.
    """
    file_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Google Drive file ID"
    )
    folder = models.ForeignKey(
        GoogleDriveFolder,
        on_delete=models.CASCADE,
        related_name='processed_files'
    )
    filename = models.CharField(max_length=500)
    processed_at = models.DateTimeField(auto_now_add=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name='processed_files'
    )

    class Meta:
        db_table = 'api_processed_files'
        verbose_name = 'Processed File'
        verbose_name_plural = 'Processed Files'
        ordering = ['-processed_at']

    def __str__(self):
        return f"Processed: {self.filename}"


class Booking(models.Model):
    """
    Model to store hotel booking data extracted from Google Sheets.
    Based on the hotel booking schema with immutable facts and mutable attributes.
    """
    # Natural key (immutable)
    booking_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Booking number (e.g., 214078)"
    )
    
    # IMMUTABLE FACTS - These should not change once set
    booking_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when booking was created"
    )
    arrive_date = models.DateField(
        null=True,
        blank=True,
        help_text="Arrival date"
    )
    depart_date = models.DateField(
        null=True,
        blank=True,
        help_text="Departure date"
    )
    original_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original total amount at time of booking"
    )
    deposit_required = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Required deposit amount"
    )
    
    # MUTABLE ATTRIBUTES - Can be updated from newer files
    status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Booking status (e.g., 'Booking', 'Confirmed', 'Cancelled')"
    )
    file_as = models.CharField(
        max_length=200,
        blank=True,
        help_text="File as name"
    )
    first_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Guest first name"
    )
    surname = models.CharField(
        max_length=100,
        blank=True,
        help_text="Guest surname"
    )
    company = models.CharField(
        max_length=200,
        blank=True,
        help_text="Company name"
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Region (e.g., 'QLD', 'NSW')"
    )
    portal = models.CharField(
        max_length=100,
        blank=True,
        help_text="Booking portal/source"
    )
    room_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Assigned room number"
    )
    room_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Room type description"
    )
    received_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount received"
    )
    deposit_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Deposit due amount"
    )
    deposit_by_date = models.DateField(
        null=True,
        blank=True,
        help_text="Deposit due by date"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current total amount"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Outstanding balance"
    )
    agent = models.CharField(
        max_length=200,
        blank=True,
        help_text="Booking agent"
    )
    agent_ref = models.CharField(
        max_length=100,
        blank=True,
        help_text="Agent reference number"
    )
    email = models.EmailField(
        blank=True,
        help_text="Guest email"
    )
    mobile = models.CharField(
        max_length=50,
        blank=True,
        help_text="Guest mobile number"
    )
    car_rego = models.CharField(
        max_length=20,
        blank=True,
        help_text="Car registration"
    )
    guest_request = models.TextField(
        blank=True,
        help_text="Special guest requests"
    )
    enquiry_status = models.CharField(
        max_length=100,
        blank=True,
        help_text="Enquiry status"
    )
    primary_source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary booking source"
    )
    black_list = models.BooleanField(
        default=False,
        help_text="Whether guest is blacklisted"
    )
    rate = models.CharField(
        max_length=200,
        blank=True,
        help_text="Rate description"
    )
    suburb = models.CharField(
        max_length=100,
        blank=True,
        help_text="Guest suburb"
    )
    post_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Guest postcode"
    )
    state = models.CharField(
        max_length=50,
        blank=True,
        help_text="Guest state"
    )
    room_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="Room status"
    )
    dual_key = models.CharField(
        max_length=50,
        blank=True,
        help_text="Dual key information"
    )
    pre_auth_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pre-authorization amount"
    )
    total_pre_auths = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total pre-authorizations"
    )
    
    # Metadata for tracking and merging
    source_file_id = models.CharField(
        max_length=255,
        help_text="Google Drive file ID where this data came from"
    )
    source_file_time = models.DateTimeField(
        help_text="Data timestamp from source file"
    )
    source_row_hash = models.CharField(
        max_length=64,
        help_text="Hash of the source row for change detection"
    )
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    
    # Django metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_bookings'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-booking_number']
        indexes = [
            models.Index(fields=['booking_number']),
            models.Index(fields=['arrive_date']),
            models.Index(fields=['status']),
            models.Index(fields=['source_file_time']),
        ]

    def __str__(self):
        return f"Booking {self.booking_number}: {self.first_name} {self.surname}"

    def calculate_row_hash(self, row_data):
        """Calculate hash of normalized row data for change detection."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(row_data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()


class BookingConflict(models.Model):
    """
    Model to track conflicts when immutable fields change.
    """
    booking_number = models.CharField(max_length=50)
    field_name = models.CharField(max_length=100)
    existing_value = models.TextField()
    incoming_value = models.TextField()
    source_file_id = models.CharField(max_length=255)
    detected_at = models.DateTimeField(auto_now_add=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name='conflicts'
    )

    class Meta:
        db_table = 'api_booking_conflicts'
        verbose_name = 'Booking Conflict'
        verbose_name_plural = 'Booking Conflicts'
        ordering = ['-detected_at']

    def __str__(self):
        return f"Conflict: {self.booking_number}.{self.field_name}"


class RawRow(models.Model):
    """
    Model to store raw row data for audit and prevent double-processing.
    """
    file_id = models.CharField(max_length=255)
    row_index = models.PositiveIntegerField()
    row_hash = models.CharField(max_length=64)
    raw_data = models.JSONField()
    processed_at = models.DateTimeField(auto_now_add=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name='raw_rows'
    )

    class Meta:
        db_table = 'api_raw_rows'
        verbose_name = 'Raw Row'
        verbose_name_plural = 'Raw Rows'
        unique_together = ['file_id', 'row_index']
        ordering = ['-processed_at']

    def __str__(self):
        return f"Row {self.row_index} from {self.file_id}"


class QuarantinedRow(models.Model):
    """
    Model to store rows that failed validation.
    """
    file_id = models.CharField(max_length=255)
    row_index = models.PositiveIntegerField()
    raw_data = models.JSONField()
    error_message = models.TextField()
    quarantined_at = models.DateTimeField(auto_now_add=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.CASCADE,
        related_name='quarantined_rows'
    )

    class Meta:
        db_table = 'api_quarantined_rows'
        verbose_name = 'Quarantined Row'
        verbose_name_plural = 'Quarantined Rows'
        ordering = ['-quarantined_at']

    def __str__(self):
        return f"Quarantined row {self.row_index}: {self.error_message[:50]}"