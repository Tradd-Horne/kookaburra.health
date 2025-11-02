"""
Views for user authentication.
"""
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from .forms import LoginForm, SignUpForm
from .models import User, PatientQuestionnaire


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


@csrf_exempt
@require_http_methods(["POST"])
def create_patient_user(request):
    """
    Create a patient user account after Step 3 of the questionnaire.
    This ensures we capture user info even if they don't complete the full form.
    """
    try:
        data = json.loads(request.body)

        # Extract required fields
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        email = data.get('email')
        phone = data.get('phone')
        password = data.get('password')

        # Validate required fields
        if not all([first_name, last_name, email, phone, password]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email already registered'
            }, status=400)

        # Create username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )

        # Create empty questionnaire record
        PatientQuestionnaire.objects.create(user=user)

        # Log the user in
        login(request, user)

        return JsonResponse({
            'success': True,
            'user_id': user.id,
            'message': 'User created successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_questionnaire(request):
    """
    Update the patient questionnaire with responses.
    Can be called multiple times to progressively save data.
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'User not authenticated'
            }, status=401)

        data = json.loads(request.body)

        # Get or create questionnaire
        questionnaire, created = PatientQuestionnaire.objects.get_or_create(
            user=request.user
        )

        # Update fields if provided
        if 'gender' in data:
            questionnaire.gender = data['gender']
        if 'genderOther' in data:
            questionnaire.gender_other = data['genderOther']
        if 'dateOfBirth' in data:
            # Parse DD/MM/YYYY format
            try:
                from datetime import datetime
                dob_str = data['dateOfBirth']
                questionnaire.date_of_birth = datetime.strptime(dob_str, '%d/%m/%Y').date()
            except:
                pass
        if 'hasMhcp' in data:
            questionnaire.has_mhcp = data['hasMhcp'] == 'yes'
        if 'sexualOrientation' in data:
            questionnaire.sexual_orientation = data['sexualOrientation']
        if 'relationshipStatus' in data:
            questionnaire.relationship_status = data['relationshipStatus']
        if 'religion' in data:
            questionnaire.religion = data['religion']
        if 'isSpiritual' in data:
            questionnaire.is_spiritual = data['isSpiritual'] == 'yes'
        if 'hasTherapyHistory' in data:
            questionnaire.has_therapy_history = data['hasTherapyHistory'] == 'yes'
        if 'isEmployed' in data:
            questionnaire.is_employed = data['isEmployed'] == 'yes'
        if 'financialStatus' in data:
            questionnaire.financial_status = data['financialStatus']

        # Mark as complete if specified
        if data.get('isComplete'):
            questionnaire.is_complete = True
            questionnaire.completed_at = timezone.now()

        questionnaire.save()

        return JsonResponse({
            'success': True,
            'message': 'Questionnaire updated successfully'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)