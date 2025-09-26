"""
Dashboard views for non-superuser interface.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm


@login_required
def dashboard_home(request):
    """Dashboard home page."""
    return render(request, 'dashboard/home.html')


@login_required
def flows(request):
    """Flows management page."""
    return render(request, 'dashboard/flows.html')


@login_required
def user_settings(request):
    """User settings page with password change."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('dashboard:settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'dashboard/settings.html', {
        'form': form
    })