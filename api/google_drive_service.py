"""
Google Drive API service for folder operations.
"""
import os
from typing import Dict, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveService:
    """Service for interacting with Google Drive API."""
    
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        
    def authenticate(self):
        """Authenticate and create Google Drive service."""
        creds = None
        
        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
                
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
                
        self.service = build('drive', 'v3', credentials=creds)
        return self.service
        
    def validate_folder(self, folder_id: str) -> Optional[Dict]:
        """
        Validate folder access and get folder details.
        
        Args:
            folder_id: Google Drive folder ID
            
        Returns:
            Dictionary with folder details or None if error
        """
        if not self.service:
            self.authenticate()
            
        try:
            # Get folder metadata
            folder = self.service.files().get(
                fileId=folder_id,
                fields="id, name, owners, modifiedTime, mimeType"
            ).execute()
            
            # Check if it's actually a folder
            if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                return None
                
            # Get file count in folder
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=1000,
                fields="files(id)"
            ).execute()
            
            file_count = len(results.get('files', []))
            
            return {
                'folder_id': folder['id'],
                'name': folder['name'],
                'owner': folder['owners'][0]['emailAddress'] if folder.get('owners') else 'Unknown',
                'file_count': file_count,
                'last_modified': folder.get('modifiedTime', ''),
                'has_access': True
            }
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
            
    def setup_watch(self, folder_id: str, webhook_url: Optional[str] = None) -> Optional[Dict]:
        """
        Set up a watch on a Google Drive folder for changes.
        
        Note: Google Drive API doesn't support webhooks for folders directly.
        This would need to use Push Notifications API or polling.
        
        Args:
            folder_id: Google Drive folder ID
            webhook_url: URL to receive notifications (optional)
            
        Returns:
            Dictionary with watch configuration or None if error
        """
        # For now, return a mock response
        # In production, you'd implement Push Notifications or polling
        return {
            'status': 'success',
            'folder_id': folder_id,
            'watch_type': 'polling',  # or 'push' if using Push Notifications
            'interval': '300',  # 5 minutes in seconds
            'webhook_url': webhook_url
        }