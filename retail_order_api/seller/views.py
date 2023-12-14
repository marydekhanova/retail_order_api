from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import requests
from yaml import load as load_yaml, YAMLError
from yaml.loader import SafeLoader
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from .permissions import IsSeller
from .serializers import ShopPriceUrlSerializer, ShopPriceSerializer, ShopStatusChangeSerializer, OrdersSerializer, OrdersItemSerializer
from products.models import Category, ProductCard, Product, Parameter, ProductParameter
from buyer.models import Order, OrderPosition
from .models import Shop


class SellerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    @property
    def user(self):
        return self.request.user


class ShopPrice(SellerAPIView):

    def post(self, request):
        serializer = ShopPriceUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        stream = requests.get(validated_data['url']).content
        try:
            data = load_yaml(stream, Loader=SafeLoader)
            serializer = ShopPriceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
            shop, created = Shop.objects.get_or_create(name=validated_data['shop'], user=request.user)
            categories = []
            for category in validated_data['categories']:
                category, created = Category.objects.get_or_create(id=category['id'], name=category['name'])
                categories.append(category)
            shop.categories.add(*categories)


            for good in validated_data['goods']:
                product, created = Product.objects.get_or_create(name=good['name'], category_id=good['category'])

                product_card, created = ProductCard.objects.update_or_create(
                    product_code=good['id'], product=product, shop=shop,
                    defaults={'model': good['model'],
                              'description': good.get('description'),
                              'price': good['price'],
                              'price_rrc': good['price_rrc'],
                              'quantity': good['quantity'],
                              'status': None}
                )

                for parameter, value in good['parameters'].items():
                    parameter, created = Parameter.objects.get_or_create(name=parameter)
                    product_parameter, created = ProductParameter.objects.update_or_create(
                    product_card=product_card, parameter=parameter, defaults={'value': value}
                    )

            return JsonResponse(validated_data)
        except YAMLError as exc:
            return JsonResponse(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                data={'yaml_error': f'{exc.__dict__["problem"].capitalize()}.'})


class ShopStatus(SellerAPIView):

    def get(self, request):
        shop = get_object_or_404(Shop, user=request.user)
        return JsonResponse({'open for orders': shop.open_for_orders})

    def patch(self, request):
        serializer = ShopStatusChangeSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        shop = get_object_or_404(Shop, user=request.user)
        shop.status = validated_data['open_for_orders']
        shop.save(update_fields=["open_for_orders"])
        return JsonResponse({'open for orders': shop.open_for_orders})


class OrdersView(SellerAPIView):

    def get(self, request):
        orders = Order.objects.filter(positions__product_card__shop=self.user.shop).order_by('-created_at')
        serializer = OrdersSerializer(orders, many=True)
        return JsonResponse({'orders': serializer.data})


class OrdersItemView(SellerAPIView):

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        seller_positions = (order.positions.filter(product_card__shop=self.user.shop).
                           select_related('product_card', 'product_card__product'))

        if not seller_positions:
            return JsonResponse({'detail': "No seller's products in order."}, status=status.HTTP_409_CONFLICT)
        order.seller_positions = seller_positions
        serializer = OrdersItemSerializer(order)
        return JsonResponse({'orders': serializer.data})