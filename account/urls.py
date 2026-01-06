from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import views for user management and authentication
from .views import (
    AddressViewSet,
    UserViewSet,
    TokenRefreshView,
    TokenVerifyView,
    TokenDestroyView,
    RequestOTP,
    VerifyOTP,
    CompleteProfileView,
    UsernamePasswordLoginView,
)

app_name = "auth"

router = DefaultRouter()
router.register(r"addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("", include(router.urls)),
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USER Authentication URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Refresh an existing JWT token
    path("token/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    # Verify an existing JWT token
    path("token/verify/", TokenVerifyView.as_view(), name="jwt-verify"),
    # Destroy an existing JWT token
    path("token/destroy/", TokenDestroyView.as_view(), name="jwt-destroy"),
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USER MANAGEMENT URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Current authenticated user endpoint with multiple HTTP methods
    path(
        "me/",
        UserViewSet.as_view({"get": "me", "put": "me", "patch": "me", "delete": "me"}),
        name="current_user",
    ),
    path(
        "staff-check/", UserViewSet.as_view({"get": "staff_check"}), name="staff_check"
    ),
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ OTP AUTHENTICATION URLS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    path("request-otp/", RequestOTP.as_view(), name="request-otp"),
    path("verify-otp/", VerifyOTP.as_view(), name="verify-otp"),
    path("complete-profile/", CompleteProfileView.as_view(), name="complete-profile"),
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ USERNAME/PASSWORD LOGIN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    path("login/", UsernamePasswordLoginView.as_view(), name="username-password-login"),
]
