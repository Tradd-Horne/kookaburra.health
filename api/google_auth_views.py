"""
Google OAuth authentication views for Django.
"""
import os
import pickle
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from google_auth_oauthlib.flow import Flow

# Google OAuth settings
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def start_google_auth(request):
    """Start Google OAuth flow."""
    if not os.path.exists(CREDENTIALS_FILE):
        return JsonResponse({'error': 'OAuth credentials not found'}, status=500)
    
    # Create flow instance
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=request.build_absolute_uri('/api/google-auth/callback/')
    )
    
    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    # Store state in session
    request.session['google_auth_state'] = state
    
    return redirect(authorization_url)

@csrf_exempt
def google_auth_callback(request):
    """Handle Google OAuth callback."""
    # Get state from session
    state = request.session.get('google_auth_state')
    if not state:
        return HttpResponse('Error: Missing state parameter', status=400)
    
    # Create flow instance
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=request.build_absolute_uri('/api/google-auth/callback/')
    )
    
    # Get authorization response
    authorization_response = request.build_absolute_uri()
    
    try:
        # Fetch token
        flow.fetch_token(authorization_response=authorization_response)
        
        # Save credentials
        credentials = flow.credentials
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        
        return HttpResponse('''
            <html>
                <body>
                    <h2>Google Drive Authentication Successful!</h2>
                    <p>You can now close this window and return to the application.</p>
                    <script>
                        // Auto-close window after 3 seconds
                        setTimeout(function() {
                            window.close();
                        }, 3000);
                    </script>
                </body>
            </html>
        ''')
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)

def auth_status(request):
    """Check Google authentication status."""
    if os.path.exists(TOKEN_FILE):
        return JsonResponse({'authenticated': True})
    else:
        return JsonResponse({'authenticated': False})