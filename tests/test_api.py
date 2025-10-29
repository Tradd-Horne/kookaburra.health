"""
Tests for API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_check(self, api_client):
        """Test that health check returns OK status."""
        url = reverse('api:health')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'status': 'ok'}
    
    def test_health_check_no_auth_required(self, api_client):
        """Test that health check doesn't require authentication."""
        url = reverse('api:health')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK