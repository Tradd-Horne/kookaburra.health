"""
Tests for users app.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test the custom User model."""
    
    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        assert user.username == 'admin'
        assert user.email == 'admin@example.com'
        assert user.is_active
        assert user.is_staff
        assert user.is_superuser
    
    def test_user_str(self):
        """Test the string representation of User."""
        user = User(username='testuser', email='test@example.com')
        assert str(user) == 'testuser'
        
        user_no_username = User(username='', email='test@example.com')
        assert str(user_no_username) == 'test@example.com'


@pytest.mark.django_db
class TestUserViews:
    """Test user authentication views."""
    
    def test_signup_view_get(self, client):
        """Test GET request to signup page."""
        url = reverse('users:signup')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'Sign Up' in response.content.decode()
    
    def test_signup_view_post(self, client):
        """Test user registration."""
        url = reverse('users:signup')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!'
        }
        
        response = client.post(url, data)
        
        assert response.status_code == 302  # Redirect after successful signup
        assert User.objects.filter(username='newuser').exists()
    
    def test_login_view_get(self, client):
        """Test GET request to login page."""
        url = reverse('users:login')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'Login' in response.content.decode()
    
    def test_login_view_post(self, client, test_user):
        """Test user login."""
        url = reverse('users:login')
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        response = client.post(url, data)
        
        assert response.status_code == 302  # Redirect after successful login
    
    def test_logout_view(self, client, test_user):
        """Test user logout."""
        client.force_login(test_user)
        
        url = reverse('users:logout')
        response = client.post(url)
        
        assert response.status_code == 302  # Redirect after logout