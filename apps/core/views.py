"""
Core views for the application.
"""
from django.shortcuts import render


def index(request):
    """Home page view."""
    return render(request, 'index.html')


def lander(request):
    """Lander page view."""
    return render(request, 'lander.html')