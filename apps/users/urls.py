"""
URL patterns for users app.
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    
    # Password reset
    path(
        'password/reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/accounts/password/reset/done/'
        ),
        name='password_reset'
    ),
    path(
        'password/reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'password/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/password/reset/complete/'
        ),
        name='password_reset_confirm'
    ),
    path(
        'password/reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
    
    # Password change
    path(
        'password/change/',
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change_form.html',
            success_url='/accounts/password/change/done/'
        ),
        name='password_change'
    ),
    path(
        'password/change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html'
        ),
        name='password_change_done'
    ),
]