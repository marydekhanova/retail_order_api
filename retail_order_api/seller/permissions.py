from rest_framework.permissions import BasePermission


class IsSeller(BasePermission):
    message = ('The user is not a seller.')

    def has_permission(self, request, view):
        if request.user.type == 'seller':
            return True


class IsProductCardOwner(BasePermission):
    message = ("The product card is not from the seller's shop.")

    def has_object_permission(self, request, view, obj):
        return request.user.shop == obj.shop

