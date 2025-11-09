from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile, TravelPreferences, UserInteraction, UserSearchHistory
import pyotp


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'phone_number', 'password', 'password_confirm']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Create related profile and preferences
        UserProfile.objects.create(user=user)
        TravelPreferences.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    mfa_code = serializers.CharField(max_length=6, required=False, allow_blank=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        mfa_code = data.get('mfa_code', '')
        
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")
        
        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_code:
                raise serializers.ValidationError("MFA code is required")
            
            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(mfa_code):
                raise serializers.ValidationError("Invalid MFA code")
        
        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['id', 'user']


class TravelPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelPreferences
        exclude = ['id', 'user']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    travel_preferences = TravelPreferencesSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'phone_number', 
                 'role', 'is_verified', 'mfa_enabled', 'date_joined', 'profile', 'travel_preferences']
        read_only_fields = ['id', 'date_joined', 'role']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone_number']


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class MFASetupSerializer(serializers.Serializer):
    enable = serializers.BooleanField(required=True)
    verification_code = serializers.CharField(max_length=6, required=False)


class UserInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInteraction
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']


class UserSearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSearchHistory
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']