#!/usr/bin/env python3
"""
One-time setup script to authenticate with Google Drive API.
Run this OUTSIDE of Docker to generate the token file.
"""

import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Same scopes as the service
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def main():
    """Authenticate with Google and save token."""
    creds = None
    credentials_file = 'credentials.json'
    token_file = 'token.pickle'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"Error: {credentials_file} not found!")
        print("Make sure you've downloaded the OAuth credentials from Google Cloud Console.")
        return
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
            print(f"Token saved to {token_file}")
    
    print("Authentication successful!")
    print("You can now use the Google Drive integration in your Django app.")

if __name__ == '__main__':
    main()