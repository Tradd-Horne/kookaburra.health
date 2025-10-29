"""
Admin configuration for API models.
"""
from django.contrib import admin

from .models import GoogleDriveFolder, GoogleDriveWatchConfig


@admin.register(GoogleDriveFolder)
class GoogleDriveFolderAdmin(admin.ModelAdmin):
    """
    Admin configuration for GoogleDriveFolder model.
    """
    list_display = [
        'folder_name', 
        'folder_id',
        'owner_email',
        'user',
        'is_active',
        'last_validated',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'created_at',
        'last_validated'
    ]
    search_fields = [
        'folder_name',
        'folder_id',
        'owner_email',
        'user__username',
        'user__email'
    ]
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(GoogleDriveWatchConfig)
class GoogleDriveWatchConfigAdmin(admin.ModelAdmin):
    """
    Admin configuration for GoogleDriveWatchConfig model.
    """
    list_display = [
        'folder',
        'user',
        'notification_type',
        'email_notifications',
        'is_active',
        'resource_id',
        'expiration',
        'created_at'
    ]
    list_filter = [
        'notification_type',
        'email_notifications',
        'is_active',
        'created_at',
        'expiration'
    ]
    search_fields = [
        'folder__folder_name',
        'folder__folder_id',
        'user__username',
        'user__email',
        'resource_id'
    ]
    readonly_fields = [
        'resource_id',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        """Optimize queries by selecting related objects."""
        qs = super().get_queryset(request)
        return qs.select_related('folder', 'user')