# users/views.py - Complete working version

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import update_session_auth_hash, authenticate
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import User, UserProfile, TravelPreferences
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserProfileSerializer, 
    TravelPreferencesSerializer, 
    UserUpdateSerializer,
    PasswordChangeSerializer, 
    MFASetupSerializer
)
from .permissions import IsOwnerOrAdmin

import logging
logger = logging.getLogger(__name__)


# ==================== REGISTRATION ====================
class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'token': str(refresh.access_token),
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


# ==================== LOGIN ====================
@method_decorator(csrf_exempt, name='dispatch')
class UserLoginView(views.APIView):
    """User login endpoint - Uses custom EmailBackend"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle login with email or username"""
        # Get credentials
        email_or_username = request.data.get('email', '').strip()
        password = request.data.get('password', '').strip()
        
        logger.info(f"🔐 Login attempt for: {email_or_username}")
        
        # Validate required fields
        if not email_or_username or not password:
            logger.warning("❌ Missing credentials")
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate using custom backend
        user = authenticate(request, username=email_or_username, password=password)
        
        if user is not None:
            logger.info(f"✅ Authentication successful for: {user.email}")
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"⚠️ Account disabled: {user.email}")
                return Response(
                    {'error': 'This account has been disabled'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            logger.info(f"🎉 Login successful - Token generated for: {user.email}")
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'token': str(refresh.access_token),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username or user.email,
                    'name': user.get_full_name(),
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"❌ Authentication failed for: {email_or_username}")
            return Response(
                {
                    'error': 'Invalid credentials',
                    'detail': 'Email or password is incorrect'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


# ==================== LOGOUT ====================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout user by blacklisting refresh token"""
    try:
        refresh_token = request.data.get('refresh') or request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Blacklist the refresh token
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
        
    except TokenError:
        return Response(
            {'error': 'Invalid or expired token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==================== USER PROFILE ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user.profile


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Get and update user details"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = UserUpdateSerializer
    
    def get_object(self):
        return self.request.user


# ==================== TRAVEL PREFERENCES ====================
class TravelPreferencesView(generics.RetrieveUpdateAPIView):
    """Get and update travel preferences"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = TravelPreferencesSerializer
    
    def get_object(self):
        return self.request.user.travel_preferences
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Mark onboarding as completed
        if not instance.onboarding_completed:
            instance.onboarding_completed = True
            instance.save()
        
        return Response(serializer.data)


# ==================== PASSWORD MANAGEMENT ====================
class PasswordChangeView(views.APIView):
    """Change user password"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        update_session_auth_hash(request, user)
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


# ==================== MFA (Multi-Factor Authentication) ====================
class MFASetupView(views.APIView):
    """Setup or disable MFA"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MFASetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        enable = serializer.validated_data['enable']
        
        if enable:
            # For now, just acknowledge the request
            # You can implement full MFA later with pyotp
            return Response({
                'message': 'MFA setup initiated',
                'mfa_enabled': False,
                'note': 'Full MFA implementation pending'
            })
        else:
            # Disable MFA
            user.mfa_enabled = False
            user.mfa_secret = None
            user.save()
            
            return Response({
                'message': 'MFA disabled successfully',
                'mfa_enabled': False
            })


# ==================== HELPER FUNCTIONS ====================
def get_tokens_for_user(user):
    """Generate JWT tokens for a user"""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }