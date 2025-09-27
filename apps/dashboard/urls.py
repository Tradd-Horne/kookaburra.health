"""
URL patterns for dashboard app.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('flows/', views.flows, name='flows'),
    path('flows/watched-folders/<str:folder_name>/', views.folder_bookings, name='folder_bookings'),
    path('settings/', views.user_settings, name='settings'),
]