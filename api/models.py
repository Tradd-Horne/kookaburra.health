"""
API models for Google Drive integration.
"""
from django.contrib.auth import get_user_model
from django.db import models

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