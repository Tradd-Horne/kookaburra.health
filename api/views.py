"""
API views.
"""
import uuid
from datetime import datetime, timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import GoogleDriveFolder, GoogleDriveWatchConfig


@extend_schema(
    summary="Health Check",
    description="Returns the health status of the API",
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "example": "ok"
                }
            }
        }
    },
    tags=["Health"]
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint.
    
    Returns a simple status to indicate the API is running.
    """
    return Response({"status": "ok"})


@extend_schema(
    summary="User Profile",
    description="Get the current authenticated user's profile information",
    responses={
        200: {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "username": {"type": "string", "example": "john_doe"},
                "email": {"type": "string", "example": "john@example.com"},
                "first_name": {"type": "string", "example": "John"},
                "last_name": {"type": "string", "example": "Doe"},
                "is_staff": {"type": "boolean", "example": False},
                "date_joined": {"type": "string", "format": "date-time"}
            }
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "Authentication credentials were not provided."}
            }
        }
    },
    tags=["User"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get the current user's profile information.
    
    Requires authentication.
    """
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "date_joined": user.date_joined,
    })


@extend_schema(
    summary="Validate Google Drive Folder",
    description="Validates access to a Google Drive folder and returns folder details",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "Google Drive folder ID",
                    "example": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                }
            },
            "required": ["folder_id"]
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "folder_id": {"type": "string", "example": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"},
                "folder_name": {"type": "string", "example": "My Documents"},
                "owner": {"type": "string", "example": "john.doe@example.com"},
                "file_count": {"type": "integer", "example": 42},
                "last_modified": {"type": "string", "format": "date-time"},
                "has_access": {"type": "boolean", "example": True}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "folder_id is required"}
            }
        },
        403: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Access denied to folder"}
            }
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Folder not found"}
            }
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "Authentication credentials were not provided."}
            }
        }
    },
    tags=["Google Drive"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_google_drive_folder(request):
    """
    Validate Google Drive folder access and return folder details.
    
    This is a mock implementation that simulates folder validation.
    In a real implementation, this would use Google Drive API to:
    - Check if the folder exists
    - Verify user has access to the folder
    - Retrieve folder metadata
    
    Requires authentication.
    """
    folder_id = request.data.get('folder_id')
    
    if not folder_id:
        return Response(
            {"error": "folder_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Mock validation logic - in real implementation, use Google Drive API
    if folder_id == "invalid_folder":
        return Response(
            {"error": "Folder not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if folder_id == "no_access_folder":
        return Response(
            {"error": "Access denied to folder"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Mock successful response
    mock_response = {
        "status": "success",
        "folder_id": folder_id,
        "folder_name": f"Sample Folder ({folder_id[:8]}...)",
        "owner": "sample.owner@example.com",
        "file_count": 42,
        "last_modified": timezone.now().isoformat(),
        "has_access": True
    }
    
    # Optionally store/update folder information in database
    try:
        folder, created = GoogleDriveFolder.objects.get_or_create(
            folder_id=folder_id,
            defaults={
                'folder_name': mock_response['folder_name'],
                'owner_email': mock_response['owner'],
                'user': request.user,
                'last_validated': timezone.now()
            }
        )
        
        if not created:
            # Update existing folder
            folder.last_validated = timezone.now()
            folder.save()
            
    except Exception as e:
        # In production, you might want to log this error
        pass
    
    return Response(mock_response, status=status.HTTP_200_OK)


@extend_schema(
    summary="Setup Google Drive Watch",
    description="Creates a watch configuration for monitoring changes in a Google Drive folder",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "Google Drive folder ID to watch",
                    "example": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                },
                "notification_type": {
                    "type": "string",
                    "enum": ["file_added", "file_removed", "file_modified", "all"],
                    "description": "Type of changes to watch for",
                    "example": "all"
                },
                "webhook_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Optional webhook URL for notifications",
                    "example": "https://myapp.com/webhook/google-drive"
                },
                "email_notifications": {
                    "type": "boolean",
                    "description": "Whether to send email notifications",
                    "example": True
                }
            },
            "required": ["folder_id"]
        }
    },
    responses={
        201: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "message": {"type": "string", "example": "Watch configuration created successfully"},
                "watch_id": {"type": "string", "example": "watch_12345"},
                "folder_id": {"type": "string", "example": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"},
                "notification_type": {"type": "string", "example": "all"},
                "email_notifications": {"type": "boolean", "example": True},
                "webhook_url": {"type": "string", "example": "https://myapp.com/webhook/google-drive"},
                "expiration": {"type": "string", "format": "date-time"},
                "created_at": {"type": "string", "format": "date-time"}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "folder_id is required"}
            }
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Folder not found or not accessible"}
            }
        },
        409: {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Watch configuration already exists for this folder"}
            }
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "Authentication credentials were not provided."}
            }
        }
    },
    tags=["Google Drive"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_google_drive_watch(request):
    """
    Setup watch configuration for a Google Drive folder.
    
    This is a mock implementation that simulates setting up a watch.
    In a real implementation, this would use Google Drive API to:
    - Create a watch request to Google Drive
    - Store the watch configuration in the database
    - Handle webhook URLs and notification preferences
    
    Requires authentication.
    """
    folder_id = request.data.get('folder_id')
    notification_type = request.data.get('notification_type', 'all')
    webhook_url = request.data.get('webhook_url')
    email_notifications = request.data.get('email_notifications', True)
    
    if not folder_id:
        return Response(
            {"error": "folder_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if folder exists and user has access (mock check)
    if folder_id == "invalid_folder":
        return Response(
            {"error": "Folder not found or not accessible"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Try to get or create the folder record
        folder, folder_created = GoogleDriveFolder.objects.get_or_create(
            folder_id=folder_id,
            defaults={
                'folder_name': f"Folder ({folder_id[:8]}...)",
                'owner_email': "unknown@example.com",
                'user': request.user,
                'last_validated': timezone.now()
            }
        )
        
        # Check if watch configuration already exists
        existing_config = GoogleDriveWatchConfig.objects.filter(
            folder=folder,
            user=request.user,
            is_active=True
        ).first()
        
        if existing_config:
            return Response(
                {"error": "Watch configuration already exists for this folder"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Create new watch configuration
        watch_config = GoogleDriveWatchConfig.objects.create(
            folder=folder,
            user=request.user,
            notification_type=notification_type,
            webhook_url=webhook_url,
            email_notifications=email_notifications,
            resource_id=f"watch_{uuid.uuid4().hex[:8]}",
            expiration=timezone.now() + timedelta(days=30)  # Mock 30-day expiration
        )
        
        # Mock successful response
        response_data = {
            "status": "success",
            "message": "Watch configuration created successfully",
            "watch_id": watch_config.resource_id,
            "folder_id": folder_id,
            "notification_type": notification_type,
            "email_notifications": email_notifications,
            "expiration": watch_config.expiration.isoformat(),
            "created_at": watch_config.created_at.isoformat()
        }
        
        if webhook_url:
            response_data["webhook_url"] = webhook_url
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to create watch configuration: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )