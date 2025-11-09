from django.urls import path
from .views import (
    UserRegistrationView, UserLoginView, UserProfileView, UserDetailView,
    TravelPreferencesView, PasswordChangeView, MFASetupView,
    get_current_user, logout_view
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', logout_view, name='user-logout'),
    path('me/', get_current_user, name='current-user'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('update/', UserDetailView.as_view(), name='user-update'),
    path('preferences/', TravelPreferencesView.as_view(), name='travel-preferences'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('mfa/setup/', MFASetupView.as_view(), name='mfa-setup'),
]