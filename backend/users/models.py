from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    role = models.CharField(max_length=20, default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # MFA fields
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=32, blank=True, null=True)
    
    # Social login
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Metadata
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Basic info
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    
    # Contact info
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"Profile of {self.user.email}"


class TravelPreferences(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='travel_preferences')
    
    # Geography preferences
    preferred_geographies = models.JSONField(default=list, blank=True)
    avoided_geographies = models.JSONField(default=list, blank=True)
    
    # Experience preferences
    preferred_experiences = models.JSONField(default=list, blank=True)
    avoided_experiences = models.JSONField(default=list, blank=True)
    
    # Landscape preferences
    preferred_landscapes = models.JSONField(default=list, blank=True)
    
    # Spiritual preferences
    spiritual_interests = models.JSONField(default=list, blank=True)
    
    # Travel style
    typical_companion_type = models.JSONField(default=list, blank=True)
    typical_budget_range = models.CharField(max_length=50, blank=True)
    typical_trip_duration = models.IntegerField(default=3, help_text='in days')
    
    # Climate preferences
    preferred_climates = models.JSONField(default=list, blank=True)
    avoided_climates = models.JSONField(default=list, blank=True)
    
    # Accessibility needs
    accessibility_requirements = models.JSONField(default=list, blank=True)
    
    # Food preferences
    dietary_restrictions = models.JSONField(default=list, blank=True)
    cuisine_preferences = models.JSONField(default=list, blank=True)
    
    # Transportation preferences
    preferred_transport_modes = models.JSONField(default=list, blank=True)
    eco_friendly_preference = models.BooleanField(default=False)
    
    # Activity preferences
    activity_level = models.CharField(max_length=20, default='moderate', 
                                     choices=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High')])
    pace_preference = models.CharField(max_length=20, default='moderate',
                                      choices=[('relaxed', 'Relaxed'), ('moderate', 'Moderate'), ('fast', 'Fast')])
    
    # Language preferences
    preferred_languages = models.JSONField(default=list, blank=True)
    
    # Metadata
    onboarding_completed = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'travel_preferences'
        verbose_name = 'Travel Preference'
        verbose_name_plural = 'Travel Preferences'
    
    def __str__(self):
        return f"Preferences of {self.user.email}"


class UserInteraction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions')
    
    interaction_type = models.CharField(max_length=50)  # view, click, search, bookmark, share
    destination_id = models.UUIDField(null=True, blank=True)
    destination_name = models.CharField(max_length=255, blank=True)
    
    # Interaction metadata
    session_id = models.CharField(max_length=100, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_interactions'
        verbose_name = 'User Interaction'
        verbose_name_plural = 'User Interactions'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['interaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.interaction_type}"


class UserSearchHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    
    query = models.TextField()
    filters_applied = models.JSONField(default=dict, blank=True)
    results_count = models.IntegerField(default=0)
    clicked_results = models.JSONField(default=list, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_search_history'
        verbose_name = 'Search History'
        verbose_name_plural = 'Search Histories'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.email} - {self.query}"