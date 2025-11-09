from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.role == 'admin':
            return True
        
        # Check if object has user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For user objects themselves
        return obj == request.user


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role == 'admin')


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    Allows access to moderators and admins.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['admin', 'moderator'])


class IsVerifiedUser(permissions.BasePermission):
    """
    Allows access only to verified users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.is_verified)