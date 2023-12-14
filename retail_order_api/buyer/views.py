from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from products.models import ProductCard
from decimal import Decimal
from rest_framework import generics
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .permissions import IsBuyer, IsOwner
from .models import CartPosition, Order, OrderPosition, Address
from products.models import ProductCard
from .serializers import CartPositionSerializer, CartSerializer, CartPositionDeleteSerializer, OrderSerializer, OrdersSerializer, AddressSerializer
from .signals import new_order
from .exceptions import LimitError


User = get_user_model()

buyer_permission_classes = [IsAuthenticated, IsBuyer]


class BuyerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsBuyer, IsOwner]

    @property
    def user(self):
        return self.request.user


class CartView(BuyerAPIView):

    def get(self, request):
        cart = self.user.cart_positions.all().select_related('product_card')
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
            'unvailable_positions': unavailable_positions}
        )
        data = serializer.data
        data['total'] = total_available_positions
        return JsonResponse(data)

    def delete(self, request):
        cart = self.user.cart_positions.all().delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


class CartPositionView(BuyerAPIView):

    def put(self, request):
        serializer = CartPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        CartPosition.objects.update_or_create(
            user=self.user,
            product_card=validated_data['product_card'],
            defaults={'quantity': validated_data['quantity']})
        return HttpResponse(status=status.HTTP_201_CREATED)

    def delete(self, request):
        serializer = CartPositionDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        cart_position = get_object_or_404(CartPosition,
                                          user=self.user,
                                          product_card=validated_data['product_card'])
        cart_position.delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


class OrdersView(BuyerAPIView):

    def get(self, request):
        data = request.query_params.get('data')
        if data:
            orders = Order.objects.filter(user=self.user, created_at__startswith=data).order_by('-created_at')
        else:
            orders = Order.objects.filter(user=self.user).order_by('-created_at')
        serializer = OrdersSerializer(orders, many=True)
        return JsonResponse({'orders': serializer.data})

    def get_address(self, address):
        address, created = Address.objects.update_or_create(
        user=self.user, **address,
        defaults={'is_active': True})
        return address

    def get_cart_positions(self):
        cart_positions = (self.user.cart_positions.filter(product_card__status='in_stock').
                          select_related('product_card'))
        return cart_positions

    def get_order(self, address, validated_data):
        order = Order(user=self.user, status='new', address=address, **validated_data)
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

    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        try:
            address = self.get_address(address=validated_data.pop('address'))
        except LimitError as err:
            return JsonResponse({'detail': f'{err}'}, status=status.HTTP_409_CONFLICT)
        cart_positions = self.get_cart_positions()
        if not cart_positions:
            return JsonResponse({'detail': 'Empty cart.'}, status=status.HTTP_409_CONFLICT)
        order = self.get_order(address=address, validated_data=validated_data)
        order_positions = self.get_order_positions(order, cart_positions)
        OrderPosition.objects.bulk_create(order_positions)
        new_order.send(sender=self.__class__, order=order, buyer_email=self.user.email)
        return JsonResponse({'order': order.id})


class OrderView(BuyerAPIView):

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        self.check_object_permissions(request, obj=order)
        serializer = OrderSerializer(order)
        return JsonResponse(serializer.data)


class AddressesView(BuyerAPIView):

    def get(self, request):
        addresses = self.user.addresses.filter(is_active=True)
        serializer = AddressSerializer(addresses, many=True)
        return JsonResponse({'addresses': serializer.data})

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
                return JsonResponse({'detail': 'The address already exists.'})
        except LimitError as err:
            return JsonResponse({'detail': f'{err}.'},
                            status=status.HTTP_409_CONFLICT)


class AddressView(BuyerAPIView):

    @property
    def address(self):
        address = get_object_or_404(Address, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj=address)
        return address

    def get(self, request, pk):
        serializer = AddressSerializer(instance=self.address)
        return JsonResponse({'addresses': serializer.data})

    def patch(self, request, pk):
        serializer = AddressSerializer(instance=self.address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_address = serializer.save()
        updated_address.save(update_fields=serializer.validated_data.keys())
        return JsonResponse(serializer.data)

    def delete(self, request, pk):
        address = self.address
        if address.orders.all() is None:
            address.delete()
        address.is_active = False
        address.save(update_fields=['is_active'])
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)



































