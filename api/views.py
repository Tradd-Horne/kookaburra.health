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

from .models import GoogleDriveFolder, GoogleDriveWatchConfig, IngestionRun
from .google_drive_service import GoogleDriveService
import pytz


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
    
    Uses Google Drive API to:
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
    
    try:
        # Initialize Google Drive service
        drive_service = GoogleDriveService()
        
        # Validate folder using Google Drive API
        folder_info = drive_service.validate_folder(folder_id)
        
        if not folder_info:
            return Response(
                {"error": "Folder not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Successful response from Google Drive API
        response_data = {
            "status": "success",
            "folder_id": folder_info['folder_id'],
            "folder_name": folder_info['name'],
            "owner": folder_info['owner'],
            "file_count": folder_info['file_count'],
            "last_modified": folder_info['last_modified'],
            "has_access": folder_info['has_access']
        }
        
        # Store/update folder information in database
        try:
            folder, created = GoogleDriveFolder.objects.get_or_create(
                folder_id=folder_id,
                defaults={
                    'folder_name': folder_info['name'],
                    'owner_email': folder_info['owner'],
                    'user': request.user,
                    'last_validated': timezone.now()
                }
            )
            
            if not created:
                # Update existing folder
                folder.folder_name = folder_info['name']
                folder.owner_email = folder_info['owner']
                folder.last_validated = timezone.now()
                folder.save()
                
        except Exception as e:
            # Log error but don't fail the API call
            print(f"Database error: {e}")
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Handle Google API errors
        error_message = str(e)
        if "HttpError 404" in error_message:
            return Response(
                {"error": "Folder not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        elif "HttpError 403" in error_message:
            return Response(
                {"error": "Access denied to folder"},
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            return Response(
                {"error": f"Google Drive API error: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    
    Uses Google Drive API to create a watch request and stores
    the configuration in the database.
    
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
    
    try:
        # Initialize Google Drive service
        drive_service = GoogleDriveService()
        
        # First validate the folder exists and user has access
        folder_info = drive_service.validate_folder(folder_id)
        if not folder_info:
            return Response(
                {"error": "Folder not found or not accessible"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Try to get or create the folder record
        folder, folder_created = GoogleDriveFolder.objects.get_or_create(
            folder_id=folder_id,
            defaults={
                'folder_name': folder_info['name'],
                'owner_email': folder_info['owner'],
                'user': request.user,
                'last_validated': timezone.now()
            }
        )
        
        # Update folder info if it already exists
        if not folder_created:
            folder.folder_name = folder_info['name']
            folder.owner_email = folder_info['owner']
            folder.last_validated = timezone.now()
            folder.save()
        
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
        
        # Setup watch using Google Drive API
        watch_result = drive_service.setup_watch(folder_id, webhook_url)
        
        if not watch_result:
            return Response(
                {"error": "Failed to setup Google Drive watch"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create new watch configuration
        watch_config = GoogleDriveWatchConfig.objects.create(
            folder=folder,
            user=request.user,
            notification_type=notification_type,
            webhook_url=webhook_url,
            email_notifications=email_notifications,
            resource_id=watch_result.get('folder_id', f"watch_{uuid.uuid4().hex[:8]}"),
            expiration=timezone.now() + timedelta(days=30)
        )
        
        # Successful response
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
        error_message = str(e)
        if "HttpError 404" in error_message:
            return Response(
                {"error": "Folder not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        elif "HttpError 403" in error_message:
            return Response(
                {"error": "Access denied to folder"},
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            return Response(
                {"error": f"Failed to create watch configuration: {error_message}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    summary="List Google Drive Watch Configurations",
    description="Get all active Google Drive watch configurations for the current user",
    responses={
        200: {
            "type": "object",
            "properties": {
                "watches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "folder_name": {"type": "string"},
                            "folder_id": {"type": "string"},
                            "status": {"type": "string"},
                            "file_count": {"type": "integer"},
                            "last_activity": {"type": "string"},
                            "expiration_date": {"type": "string"},
                            "days_until_expiration": {"type": "integer"},
                            "last_validated": {"type": "string"},
                            "watch_type": {"type": "string"},
                            "created_date": {"type": "string"}
                        }
                    }
                }
            }
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"}
            }
        }
    },
    tags=["Google Drive"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_google_drive_watches(request):
    """
    List all active Google Drive watch configurations for the current user.
    
    Returns real-time data about watched folders including connection status,
    expiration dates, and last activity times in Queensland timezone.
    """
    try:
        # Get Queensland timezone
        qld_tz = pytz.timezone('Australia/Brisbane')
        
        # Get all active watch configurations for the user
        watch_configs = GoogleDriveWatchConfig.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('folder').order_by('-created_at')
        
        # Initialize Google Drive service for real-time data
        drive_service = GoogleDriveService()
        
        watches = []
        for config in watch_configs:
            folder = config.folder
            
            # Get real-time folder data
            try:
                folder_info = drive_service.validate_folder(folder.folder_id)
                if folder_info:
                    file_count = folder_info['file_count']
                    connection_status = "Connected"
                    last_activity = folder_info.get('last_modified', '')
                else:
                    file_count = 0
                    connection_status = "Disconnected"
                    last_activity = ""
                    
            except Exception as e:
                file_count = 0
                connection_status = "Error"
                last_activity = ""
            
            # Calculate days until expiration
            now = timezone.now()
            days_until_expiration = (config.expiration - now).days if config.expiration > now else 0
            
            # Convert timestamps to Queensland time with DD-MM-YYYY format
            last_validated_qld = folder.last_validated.astimezone(qld_tz).strftime('%d-%m-%Y %I:%M:%S %p AEST')
            created_qld = config.created_at.astimezone(qld_tz).strftime('%d-%m-%Y %I:%M:%S %p AEST')
            expiration_qld = config.expiration.astimezone(qld_tz).strftime('%d-%m-%Y %I:%M:%S %p AEST')
            
            # Generate Google Drive folder URL
            folder_url = f"https://drive.google.com/drive/folders/{folder.folder_id}"
            
            watch_data = {
                "id": config.id,
                "folder_name": folder.folder_name,
                "folder_id": folder.folder_id,
                "folder_url": folder_url,
                "status": connection_status,
                "file_count": file_count,
                "last_activity": last_activity,
                "expiration_date": expiration_qld,
                "days_until_expiration": days_until_expiration,
                "last_validated": last_validated_qld,
                "watch_type": "Google Drive Folder",
                "created_date": created_qld,
                "notification_type": config.notification_type,
                "email_notifications": config.email_notifications
            }
            
            watches.append(watch_data)
        
        return Response({"watches": watches}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch watch configurations: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Import Booking Data",
    description="Manually trigger import of booking data from Google Sheets in watched folders",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "folder_id": {
                    "type": "string",
                    "description": "Specific folder ID to process (optional - if not provided, processes all watched folders)",
                    "example": "1ZUp72GiB8CTz187XV_4nL3OzMYq-InPK"
                }
            }
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "success"},
                "message": {"type": "string", "example": "Import completed successfully"},
                "summary": {
                    "type": "object",
                    "properties": {
                        "folders_processed": {"type": "integer"},
                        "files_discovered": {"type": "integer"},
                        "files_processed": {"type": "integer"},
                        "bookings_inserted": {"type": "integer"},
                        "bookings_updated": {"type": "integer"},
                        "conflicts_detected": {"type": "integer"},
                        "rows_quarantined": {"type": "integer"}
                    }
                },
                "results": {"type": "array", "items": {"type": "object"}}
            }
        },
        400: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
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
                "detail": {"type": "string"}
            }
        }
    },
    tags=["Google Sheets"]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_booking_data(request):
    """
    Import booking data from Google Sheets in watched folders.
    
    Triggers the complete discovery → extraction → merge → dedupe pipeline
    for hotel booking data from Google Sheets files.
    
    This implements your step-by-step process:
    1. Discover new Google Sheets files in watched folders
    2. Extract booking data with field mapping and validation
    3. Merge with existing data using latest-wins for mutable attributes
    4. Deduplicate based on booking number (natural key)
    5. Store in PostgreSQL with full audit trail
    
    Requires authentication.
    """
    try:
        from .booking_ingestion_service import BookingIngestionService
        
        folder_id = request.data.get('folder_id')
        
        # Get folders to process
        if folder_id:
            # Process specific folder
            try:
                folders = [GoogleDriveFolder.objects.get(
                    folder_id=folder_id,
                    user=request.user,
                    is_active=True
                )]
            except GoogleDriveFolder.DoesNotExist:
                return Response(
                    {"error": "Folder not found or not accessible"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Process all user's watched folders
            folders = GoogleDriveFolder.objects.filter(
                user=request.user,
                is_active=True
            )
        
        if not folders:
            return Response(
                {"error": "No watched folders found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize ingestion service
        ingestion_service = BookingIngestionService()
        
        # Process each folder
        results = []
        summary = {
            'folders_processed': 0,
            'files_discovered': 0,
            'files_processed': 0,
            'files_failed': 0,
            'bookings_inserted': 0,
            'bookings_updated': 0,
            'bookings_ignored': 0,
            'conflicts_detected': 0,
            'rows_quarantined': 0
        }
        
        for folder in folders:
            print(f"Processing folder: {folder.folder_name}")
            folder_result = ingestion_service.process_folder(folder)
            results.append(folder_result)
            
            # Aggregate summary
            summary['folders_processed'] += 1
            summary['files_discovered'] += folder_result.get('files_discovered', 0)
            summary['files_processed'] += folder_result.get('files_processed', 0)
            summary['files_failed'] += folder_result.get('files_failed', 0)
            summary['bookings_inserted'] += folder_result.get('total_bookings_inserted', 0)
            summary['bookings_updated'] += folder_result.get('total_bookings_updated', 0)
            summary['bookings_ignored'] += folder_result.get('total_bookings_ignored', 0)
            summary['conflicts_detected'] += folder_result.get('total_conflicts', 0)
            summary['rows_quarantined'] += folder_result.get('total_quarantined', 0)
        
        # Generate summary message
        if summary['files_processed'] == 0:
            message = "No new files found to process"
        else:
            message = f"Processed {summary['files_processed']} files: " \
                     f"{summary['bookings_inserted']} new bookings, " \
                     f"{summary['bookings_updated']} updated"
            
            if summary['conflicts_detected'] > 0:
                message += f", {summary['conflicts_detected']} conflicts detected"
                
            if summary['rows_quarantined'] > 0:
                message += f", {summary['rows_quarantined']} rows quarantined"
        
        return Response({
            "status": "success",
            "message": message,
            "summary": summary,
            "results": results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Import failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get Last Import Info",
    description="Get information about the most recent booking data import",
    responses={
        200: {
            "type": "object",
            "properties": {
                "last_import": {
                    "type": "object",
                    "properties": {
                        "completed_at": {"type": "string", "format": "date-time"},
                        "formatted_time": {"type": "string"},
                        "filename": {"type": "string"},
                        "status": {"type": "string"},
                        "rows_inserted": {"type": "integer"},
                        "rows_updated": {"type": "integer"}
                    }
                }
            }
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {"type": "string"}
            }
        }
    },
    tags=["Google Sheets"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_last_import_info(request):
    """
    Get information about the most recent booking data import.
    
    Returns the timestamp, filename, and status of the last completed
    ingestion run for the current user's watched folders.
    """
    try:
        # Get Queensland timezone
        qld_tz = pytz.timezone('Australia/Brisbane')
        
        # Get user's folders
        user_folders = GoogleDriveFolder.objects.filter(
            user=request.user,
            is_active=True
        )
        
        if not user_folders.exists():
            return Response({
                "last_import": None,
                "message": "No watched folders found"
            }, status=status.HTTP_200_OK)
        
        # Get the most recent completed ingestion run across all user's folders
        last_import = IngestionRun.objects.filter(
            folder__in=user_folders,
            completed_at__isnull=False
        ).order_by('-completed_at').first()
        
        if not last_import:
            return Response({
                "last_import": None,
                "message": "No imports have been completed yet"
            }, status=status.HTTP_200_OK)
        
        # Format the time in Queensland timezone
        completed_qld = last_import.completed_at.astimezone(qld_tz)
        formatted_time = completed_qld.strftime('%d-%m-%Y %I:%M:%S %p AEST')
        
        return Response({
            "last_import": {
                "completed_at": last_import.completed_at.isoformat(),
                "formatted_time": formatted_time,
                "filename": last_import.filename,
                "status": last_import.status,
                "rows_inserted": last_import.rows_inserted,
                "rows_updated": last_import.rows_updated,
                "rows_quarantined": last_import.rows_quarantined
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get import info: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    summary="Get Folder Statistics",
    description="Get statistics about a specific Google Drive folder's processed data",
    responses={
        200: {
            "type": "object",
            "properties": {
                "folder_name": {"type": "string"},
                "booking_count": {"type": "integer"},
                "last_import": {"type": "string", "format": "date-time"}
            }
        },
        404: {
            "type": "object",
            "properties": {
                "error": {"type": "string"}
            }
        }
    },
    tags=["Google Sheets"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_folder_statistics(request):
    """
    Get statistics about a specific folder's processed booking data.
    """
    folder_name = request.GET.get('folder_name')
    
    if not folder_name:
        return Response(
            {"error": "folder_name parameter is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get the folder for the current user
        folder = GoogleDriveFolder.objects.filter(
            folder_name=folder_name,
            user=request.user,
            is_active=True
        ).first()
        
        if not folder:
            return Response(
                {"error": "Folder not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get booking count
        booking_count = Booking.objects.filter(
            ingestion_run__folder=folder
        ).count()
        
        # Get last import
        last_import = IngestionRun.objects.filter(
            folder=folder,
            completed_at__isnull=False
        ).order_by('-completed_at').first()
        
        return Response({
            "folder_name": folder.folder_name,
            "booking_count": booking_count,
            "last_import": last_import.completed_at.isoformat() if last_import else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get folder statistics: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )