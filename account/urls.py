from django.urls import path

# Import views for user management and authentication
from .views import (
    UserViewSet,
    TokenRefreshView,
    TokenVerifyView,
    TokenDestroyView, RequestOTP,
    VerifyOTP,
    CompleteProfileView,
)

# Application namespace to avoid conflicts
app_name = 'auth'

urlpatterns = [
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USER Authentication URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Refresh an existing JWT token
    path('token/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),

    # Verify an existing JWT token
    path('token/verify/', TokenVerifyView.as_view(), name='jwt-verify'),

    # Destroy an existing JWT token
    path('token/destroy/', TokenDestroyView.as_view(), name='jwt-destroy'),
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USER MANAGEMENT URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Current authenticated user endpoint with multiple HTTP methods
    path(
        'me/',
        UserViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me', 'delete': 'me'}),
        name='current_user'
    ),
    path('staff-check/', UserViewSet.as_view({'get': 'staff_check'}), name='staff_check'),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ OTP AUTHENTICATION URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    path('request-otp/', RequestOTP.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTP.as_view(), name='verify-otp'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete-profile'),
]

