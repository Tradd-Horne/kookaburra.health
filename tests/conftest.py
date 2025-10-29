"""
Pytest configuration and fixtures.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpassword123',
        first_name='Test',
        last_name='User'
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpassword123'
    )
    return user


@pytest.fixture
def api_client():
    """Create an API client."""
    from rest_framework.test import APIClient
    return APIClient()