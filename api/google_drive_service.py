"""
Google Drive API service for folder operations.
"""
import os
from typing import Dict, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes for Service Account
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]


class GoogleDriveService:
    """Service for interacting with Google Drive API using Service Account."""
    
    def __init__(self, service_account_file='service-account.json'):
        self.service_account_file = service_account_file
        self.service = None
        
    def authenticate(self):
        """Authenticate using Service Account and create Google Drive service."""
        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(f"Service account file {self.service_account_file} not found")
        
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, 
            scopes=SCOPES
        )
        
        # Build the service
        self.service = build('drive', 'v3', credentials=credentials)
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
    
    def get_file_metadata(self, file_id: str) -> dict:
        """Get metadata for a specific file by ID."""
        try:
            service = self.authenticate()
            metadata = service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,size,createdTime,modifiedTime,parents'
            ).execute()
            return metadata
        except Exception as e:
            print(f"Error getting file metadata: {e}")
            return None
    
    def list_files_in_folder(self, folder_id: str) -> list:
        """List all files in a specific Google Drive folder."""
        try:
            service = self.authenticate()
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id,name,mimeType,size,createdTime,modifiedTime,parents)',
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            return files
            
        except Exception as e:
            print(f"Error listing files in folder {folder_id}: {e}")
            return []