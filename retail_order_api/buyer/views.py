from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.http import JsonResponse, HttpResponse
from rest_framework import status, serializers
from decimal import Decimal
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .permissions import IsBuyer, IsOwner
from .models import CartPosition, Order, OrderPosition, Address
from products.models import ProductCard
from .serializers import (CartPositionSerializer, CartSerializer,
                          CartPositionDeleteSerializer,
                          OrderSerializer, OrderListSerializer, AddressSerializer, OrderNewSerializer)
from .signals import new_order
from .exceptions import LimitError
from retail_order_api.docs_responses import (response_unauthorized, DetailResponseSerializer,
                                             IncorrectDataSerializer)


User = get_user_model()

responses_no_access = {**response_unauthorized,
                       status.HTTP_403_FORBIDDEN: OpenApiResponse(response=DetailResponseSerializer,
                                                                  description='The user is not a buyer.'),
                       }


class BuyerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBuyer, IsOwner]

    @property
    def user(self):
        return self.request.user


@extend_schema(tags=["buyer’s cart"])
class CartView(BuyerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: CartSerializer,
                   **responses_no_access}
    )
    def get(self, request):
        cart = self.user.cart_positions.all().select_related('product_card')
        if not cart:
            return JsonResponse(data={})
        unavailable_positions = []
        available_positions = []
        total_available_positions = 0
        for position in cart:
            product_card = position.product_card
            if product_card.status in ['withdrawn', 'sold']:
                unavailable_positions.append(position)
                continue
            if position.quantity > product_card.quantity:
                position.quantity = product_card.quantity
                position.save()
            available_positions.append(position)
            total_available_positions += position.price_per_quantity
        serializer = CartSerializer({
            'available_positions': available_positions,
            'unvailable_positions': unavailable_positions,
            'total': total_available_positions
        }
        )
        data = serializer.data
        return JsonResponse(data)

    @extend_schema(
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   **responses_no_access}
    )
    def delete(self, request):
        cart = self.user.cart_positions.all().delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["buyer’s cart"])
class CartPositionView(BuyerAPIView):

    @extend_schema(
        request=CartPositionSerializer,
        responses={status.HTTP_201_CREATED: OpenApiResponse(description='Created.'),
                   status.HTTP_204_NO_CONTENT: OpenApiResponse(description='Updated.'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **responses_no_access}
    )
    def put(self, request):
        serializer = CartPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        cart_position, created = CartPosition.objects.update_or_create(
            user=self.user,
            product_card=validated_data['product_card'],
            defaults={'quantity': validated_data['quantity']})
        if created:
            return HttpResponse(status=status.HTTP_201_CREATED)
        else:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Product card is not in the cart.'),
                   **responses_no_access}
    )
    def delete(self, request):
        serializer = CartPositionDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        product_card = validated_data['product_card']
        try:
            cart_position = CartPosition.objects.get(
                user=self.user,
                product_card=product_card)
        except CartPosition.DoesNotExist:
            return JsonResponse(
                {"detail": f"Product card with id '{product_card.id}' is not in the cart."},
                status=status.HTTP_404_NOT_FOUND)
        cart_position.delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["buyer’s orders"])
class OrdersView(BuyerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: OrderListSerializer(many=True),
                   **responses_no_access}
    )
    def get(self, request):
        data = request.query_params.get('data')
        if data:
            orders = Order.objects.filter(user=self.user, created_at__startswith=data).order_by('-created_at')
        else:
            orders = Order.objects.filter(user=self.user).order_by('-created_at')
        serializer = OrderListSerializer(orders, many=True)
        return JsonResponse(serializer.data, safe=False)

    def update_or_create_address(self, address):
        address, created = Address.objects.update_or_create(
        user=self.user, **address,
        defaults={'is_active': True})
        return address

    def get_cart_positions(self):
        cart_positions = (self.user.cart_positions.filter(product_card__status='in_stock').
                          select_related('product_card'))
        return cart_positions

    def create_order(self, address, validated_data):
        order = Order(user=self.user, address=address, **validated_data)
        order.save()
        return order

    def get_order_positions(self, order, cart_positions):
        order_positions = []
        for position in cart_positions:
            product_card = position.product_card
            order_position = OrderPosition(order=order,
                                           product_card=product_card,
                                           price=product_card.price,
                                           quantity=position.quantity
                                           )
            order_positions.append(order_position)
            product_card.quantity -= position.quantity
            position.delete()
            product_card.save(update_fields=['quantity', 'status'])
        return order_positions

    @extend_schema(
        request=OrderSerializer,
        responses={status.HTTP_201_CREATED: OrderNewSerializer,
                   status.HTTP_409_CONFLICT: OpenApiResponse(
                       response=DetailResponseSerializer,
                       description='No more than 5 addresses per user or cart is empty.'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **responses_no_access}
    )
    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        try:
            address = self.update_or_create_address(address=validated_data.pop('address'))
        except LimitError as err:
            return JsonResponse({'detail': f'{err}'}, status=status.HTTP_409_CONFLICT)
        cart_positions = self.get_cart_positions()
        if not cart_positions:
            return JsonResponse({'detail': 'Empty cart.'}, status=status.HTTP_409_CONFLICT)
        order = self.create_order(address=address, validated_data=validated_data)
        order_positions = self.get_order_positions(order, cart_positions)
        OrderPosition.objects.bulk_create(order_positions)
        new_order.send(sender=self.__class__, order=order, buyer_email=self.user.email)
        serializer = OrderNewSerializer(order)
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["buyer’s orders"])
class OrderView(BuyerAPIView):

    @extend_schema(
    responses = {status.HTTP_200_OK: OrderSerializer,
                 status.HTTP_404_NOT_FOUND: OpenApiResponse(
                     response=DetailResponseSerializer,
                     description='Order not found.'),
                 **responses_no_access}
    )
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        self.check_object_permissions(request, obj=order)
        serializer = OrderSerializer(order)
        return JsonResponse(serializer.data)


@extend_schema(tags=["buyer’s addresses"])
class AddressesView(BuyerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: AddressSerializer,
                   ** responses_no_access}
    )
    def get(self, request):
        addresses = self.user.addresses.filter(is_active=True)
        serializer = AddressSerializer(addresses, many=True)
        return JsonResponse(serializer.data, safe=False)

    @extend_schema(
        request=AddressSerializer,
        responses={status.HTTP_201_CREATED: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_409_CONFLICT: OpenApiResponse(response=DetailResponseSerializer,
                                                                description=
                                                                f'The address already exists '
                                                                f'or the limit on the number '
                                                                f'of addresses has been exceeded.'),
                   **responses_no_access}
    )
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        try:
            address, created = Address.objects.get_or_create(user=self.user, **validated_data)
            if created or (address.is_active == False):
                address.is_active = True
                address.save(update_fields=['is_active'])
                return HttpResponse(status=status.HTTP_201_CREATED)
            if address.is_active:
                return JsonResponse({'detail': 'The address already exists.'}, status=status.HTTP_409_CONFLICT)
        except LimitError as err:
            return JsonResponse({'detail': f'{err}.'},
                            status=status.HTTP_409_CONFLICT)


@extend_schema(tags=["buyer’s addresses"])
class AddressView(BuyerAPIView):

    @property
    def address(self):
        address = get_object_or_404(Address, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj=address)
        return address

    @extend_schema(
        responses={status.HTTP_200_OK: AddressSerializer,
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(
                       response=DetailResponseSerializer,
                       description='Address not found.'),
                   **responses_no_access}
    )
    def get(self, request, pk):
        serializer = AddressSerializer(instance=self.address)
        return JsonResponse({'addresses': serializer.data})

    @extend_schema(
        request=AddressSerializer,
        responses={status.HTTP_200_OK: AddressSerializer,
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(
                       response=DetailResponseSerializer,
                       description='Address not found.'),
                   **responses_no_access}
    )
    def patch(self, request, pk):
        serializer = AddressSerializer(instance=self.address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_address = serializer.save()
        updated_address.save(update_fields=serializer.validated_data.keys())
        return JsonResponse(serializer.data)

    @extend_schema(
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(
                       response=DetailResponseSerializer,
                       description='Address not found.'),
                   **responses_no_access}
    )
    def delete(self, request, pk):
        address = self.address
        if address.orders.all() is None:
            address.delete()
        address.is_active = False
        address.save(update_fields=['is_active'])
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)



































