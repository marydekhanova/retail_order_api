from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    message = ('The user is not a buyer.')

    def has_permission(self, request, view):
        return request.user.type == 'buyer'


class IsOwner(BasePermission):
    message = ('The user is not the owner.')

    def has_object_permission(self, request, view, obj):
       return request.user == obj.user
