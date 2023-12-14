from rest_framework.permissions import BasePermission


class IsSeller(BasePermission):
    message = ('The user is not a seller.')

    def has_permission(self, request, view):
        if request.user.type == 'seller':
            return True
