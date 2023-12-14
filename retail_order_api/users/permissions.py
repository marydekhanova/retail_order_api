from rest_framework.permissions import BasePermission


class IsAuthenticatedOrCreateOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        if request.method in ['GET', 'PATCH']:
            if request.user.is_authenticated:
                return True
