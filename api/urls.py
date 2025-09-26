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
    
    # API documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]