"""
API URL configuration.
"""
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from . import views

app_name = 'api'

urlpatterns = [
    # API health check
    path('health/', views.health_check, name='health'),
    
    # User endpoints
    path('user/profile/', views.user_profile, name='user_profile'),
    
    # Google Drive endpoints
    path('google-drive/validate-folder/', views.validate_google_drive_folder, name='validate_google_drive_folder'),
    path('google-drive/setup-watch/', views.setup_google_drive_watch, name='setup_google_drive_watch'),
    
    # API documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]