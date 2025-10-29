"""
Views for user authentication.
"""
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, SignUpForm
from .models import User


class SignUpView(CreateView):
    """User registration view."""
    
    model = User
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('users:login')
    
    def form_valid(self, form):
        """If the form is valid, save the user and log them in."""
        user = form.save()
        login(self.request, user)
        # Redirect superusers to admin, regular users to dashboard
        if user.is_superuser:
            return redirect('/')
        else:
            return redirect('/dashboard/')
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect to home if user is already authenticated."""
        if request.user.is_authenticated:
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


class LoginView(BaseLoginView):
    """Custom login view."""
    
    form_class = LoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Return the success URL."""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        # Redirect superusers to admin, regular users to dashboard
        if self.request.user.is_superuser:
            return '/'
        else:
            return '/dashboard/'


class LogoutView(BaseLogoutView):
    """Custom logout view."""
    
    next_page = '/'