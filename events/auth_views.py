"""
Authentication views for user registration and login.

Provides JWT token-based authentication endpoints.

IMPORTANT: These endpoints are PUBLIC (not JWT protected) using @permission_classes([AllowAny])
to allow users to register and login without authentication.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django_ratelimit.decorators import ratelimit
from rest_framework_simplejwt.tokens import RefreshToken


# Rate limiting: 5 registrations per hour per IP to prevent abuse
@ratelimit(key='ip', rate='5/h', method='POST')
@api_view(['POST'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user and return JWT tokens.
    
    POST /api/auth/register/
    {
        "username": "user123",
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_201_CREATED)


# Rate limiting: 10 login attempts per minute per IP to prevent brute force
@ratelimit(key='ip', rate='10/m', method='POST')
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny]) 
def login(request):
    """
    Authenticate user and return JWT tokens.
    
    POST /api/auth/login/
    {
        "username": "user123",
        "password": "securepassword"
    }
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    }, status=status.HTTP_200_OK)


# PUBLIC ENDPOINT - No JWT authentication required (only needs refresh token in body)
@api_view(['POST'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Refresh access token using refresh token.
    
    POST /api/auth/refresh/
    {
        "refresh": "refresh_token_string"
    }
    """
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

