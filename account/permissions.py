from rest_framework import permissions


class IsProfileIncomplete(permissions.BasePermission):
    """
    Allows access only to users with incomplete profiles.
    """

    message = "Profile is already complete."

    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_profile_complete
