from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import requests
from yaml import load as load_yaml, YAMLError
from yaml.loader import SafeLoader
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .permissions import IsSeller
from .serializers import (ShopPricesUrlSerializer, ShopPricesSerializer, ShopStatusSerializer,
                          OrdersSerializer, OrdersItemSerializer, YamlErrorSerializer)
from products.models import Category, ProductCard, Product, Parameter, ProductParameter
from buyer.models import Order, OrderPosition
from .models import Shop
from retail_order_api.docs_responses import (response_unauthorized, DetailResponseSerializer,
                                             IncorrectDataSerializer)


responses_no_access = {**response_unauthorized,
                       status.HTTP_403_FORBIDDEN: OpenApiResponse(response=DetailResponseSerializer,
                                                                  description='The user is not a seller.'),
                       }


class SellerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]

    @property
    def user(self):
        return self.request.user


@extend_schema(tags=["shop"])
class ShopPrices(SellerAPIView):

    @extend_schema(
        request=ShopPricesUrlSerializer,
        responses={status.HTTP_200_OK: ShopPricesSerializer,
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_422_UNPROCESSABLE_ENTITY: OpenApiResponse(response=YamlErrorSerializer),
                   **responses_no_access}
    )
    def post(self, request):
        serializer = ShopPricesUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        stream = requests.get(validated_data['url']).content
        try:
            data = load_yaml(stream, Loader=SafeLoader)
            serializer = ShopPricesSerializer(data=data)
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


@extend_schema(tags=["shop"])
class ShopStatus(SellerAPIView):

    @extend_schema(
        request=ShopPricesUrlSerializer,
        responses={status.HTTP_200_OK: ShopStatusSerializer,
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_422_UNPROCESSABLE_ENTITY: OpenApiResponse(response=YamlErrorSerializer),
                   **responses_no_access}
    )
    def get(self, request):
        shop = get_object_or_404(Shop, user=request.user)
        serializer = ShopStatusSerializer(shop)
        return JsonResponse(serializer.data)

    @extend_schema(
        request=ShopStatusSerializer,
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Shop not found.'),
                   **responses_no_access}
    )
    def patch(self, request):
        serializer = ShopStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        shop = get_object_or_404(Shop, user=request.user)
        shop.open_for_orders = validated_data['open_for_orders']
        shop.save(update_fields=["open_for_orders"])
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["seller's orders"])
class OrdersView(SellerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: OrdersSerializer(many=True),
                   **responses_no_access}
    )
    def get(self, request):
        orders = Order.objects.filter(positions__product_card__shop=self.user.shop).order_by('-created_at')
        serializer = OrdersSerializer(orders, many=True)
        return JsonResponse(serializer.data, safe=False)


@extend_schema(tags=["seller's orders"])
class OrdersItemView(SellerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: OrdersItemSerializer,
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Order not found.'),
                   status.HTTP_409_CONFLICT: OpenApiResponse(response=DetailResponseSerializer,
                                                              description="No seller's products in order."),
                   **responses_no_access}
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        seller_positions = (order.positions.filter(product_card__shop=self.user.shop).
                           select_related('product_card', 'product_card__product'))

        if not seller_positions:
            return JsonResponse({'detail': "No seller's products in order."}, status=status.HTTP_409_CONFLICT)
        order.seller_positions = seller_positions
        serializer = OrdersItemSerializer(order)
        return JsonResponse(serializer.data)