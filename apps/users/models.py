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
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Timestamps (date_joined and last_login are already included)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username or self.email


class PatientQuestionnaire(models.Model):
    """
    Model to store patient questionnaire responses.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='questionnaire')

    # Personal Information
    gender = models.CharField(max_length=50, blank=True, null=True)
    gender_other = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    # MHCP Information
    has_mhcp = models.BooleanField(default=False)
    mhcp_file = models.FileField(upload_to='mhcp_files/', blank=True, null=True)

    # Identity Information
    sexual_orientation = models.CharField(max_length=50, blank=True, null=True)
    relationship_status = models.CharField(max_length=50, blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    is_spiritual = models.BooleanField(blank=True, null=True)

    # Therapy & Background
    has_therapy_history = models.BooleanField(blank=True, null=True)
    is_employed = models.BooleanField(blank=True, null=True)
    financial_status = models.CharField(max_length=20, blank=True, null=True)

    # Completion tracking
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patient_questionnaires'
        verbose_name = 'Patient Questionnaire'
        verbose_name_plural = 'Patient Questionnaires'
        ordering = ['-created_at']

    def __str__(self):
        return f"Questionnaire for {self.user.email}"