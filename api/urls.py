"""
API URL configuration.
"""
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from . import views, google_auth_views

app_name = 'api'

urlpatterns = [
    # API health check
    path('health/', views.health_check, name='health'),
    
    # User endpoints
    path('user/profile/', views.user_profile, name='user_profile'),
    
    # Google Drive endpoints
    path('google-drive/validate-folder/', views.validate_google_drive_folder, name='validate_google_drive_folder'),
    path('google-drive/setup-watch/', views.setup_google_drive_watch, name='setup_google_drive_watch'),
    path('google-drive/list-watches/', views.list_google_drive_watches, name='list_google_drive_watches'),
    path('google-drive/delete-watch/', views.delete_google_drive_watch, name='delete_google_drive_watch'),
    path('google-drive/list-inactive-folders/', views.list_inactive_folders_with_data, name='list_inactive_folders_with_data'),
    
    # Google Sheets endpoints
    path('google-sheets/import-bookings/', views.import_booking_data, name='import_booking_data'),
    path('google-sheets/last-import/', views.get_last_import_info, name='get_last_import_info'),
    path('google-sheets/folder-stats/', views.get_folder_statistics, name='get_folder_statistics'),
    
    # Google OAuth endpoints
    path('google-auth/start/', google_auth_views.start_google_auth, name='start_google_auth'),
    path('google-auth/callback/', google_auth_views.google_auth_callback, name='google_auth_callback'),
    path('google-auth/status/', google_auth_views.auth_status, name='auth_status'),
    
    # API documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]