from rest_framework import permissions


class IsProfileIncomplete(permissions.BasePermission):
    """
    Allows access only to users with incomplete profiles.
    """

    message = "Profile is already complete."

    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_profile_complete


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet or admin users.
        return obj.user == request.user or request.user.is_staff
