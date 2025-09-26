"""
Custom user model.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    
    Inherits:
        - username
        - email
        - password
        - first_name
        - last_name
        - is_staff
        - is_superuser
        - is_active
        - date_joined
        - last_login
        - groups
        - user_permissions
    """
    
    # Additional fields can be added here
    email = models.EmailField(unique=True, blank=False, null=False)
    
    # Timestamps (date_joined and last_login are already included)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.username or self.email