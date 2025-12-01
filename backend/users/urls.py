from django.urls import path
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserDetailView,
    TravelPreferencesView,
    PasswordChangeView,
    MFASetupView,
    get_current_user,
    logout_view
)

urlpatterns = [
    # Use the class-based login view (properly handles ASGI)
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('logout/', logout_view, name='user-logout'),
    
    # User profile and preferences
    path('me/', get_current_user, name='current-user'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('details/', UserDetailView.as_view(), name='user-detail'),
    path('preferences/', TravelPreferencesView.as_view(), name='travel-preferences'),
    
    # Security
    path('change-password/', PasswordChangeView.as_view(), name='password-change'),
    path('mfa-setup/', MFASetupView.as_view(), name='mfa-setup'),
]