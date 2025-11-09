from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import update_session_auth_hash
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
from .authentication import generate_mfa_secret, generate_qr_code, verify_mfa_code, get_tokens_for_user
from .permissions import IsOwnerOrAdmin
from rest_framework.decorators import api_view, permission_classes


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):  # ← Make sure this is NOT async
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(views.APIView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):  # ← Make sure this is NOT async
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)


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
        
        # Mark onboarding as completed if not already
        if not instance.onboarding_completed:
            instance.onboarding_completed = True
            instance.save()
        
        return Response(serializer.data)


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


class MFASetupView(views.APIView):
    """Setup or disable MFA"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MFASetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        enable = serializer.validated_data['enable']
        
        if enable:
            # Generate new secret if not exists
            if not user.mfa_secret:
                user.mfa_secret = generate_mfa_secret()
                user.save()
            
            # Generate QR code
            qr_code = generate_qr_code(user, user.mfa_secret)
            
            # If verification code provided, enable MFA
            if 'verification_code' in serializer.validated_data:
                code = serializer.validated_data['verification_code']
                if verify_mfa_code(user, code):
                    user.mfa_enabled = True
                    user.save()
                    return Response({
                        'message': 'MFA enabled successfully',
                        'mfa_enabled': True
                    })
                else:
                    return Response({
                        'error': 'Invalid verification code'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'qr_code': qr_code,
                'secret': user.mfa_secret,
                'message': 'Scan QR code with authenticator app'
            })
        else:
            # Disable MFA
            verification_code = serializer.validated_data.get('verification_code')
            if not verification_code or not verify_mfa_code(user, verification_code):
                return Response({
                    'error': 'Verification code required to disable MFA'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.mfa_enabled = False
            user.mfa_secret = None
            user.save()
            
            return Response({
                'message': 'MFA disabled successfully',
                'mfa_enabled': False
            })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user by blacklisting refresh token
    """
    try:
        # Get refresh token from request
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
            'message': 'Logged out successfully. Token has been blacklisted.'
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