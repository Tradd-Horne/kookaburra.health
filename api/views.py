"""
API views.
"""
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


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