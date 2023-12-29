from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import requests
from urllib3 import request
from yaml import load as load_yaml, YAMLError
from yaml.loader import SafeLoader
from django.http import JsonResponse, HttpResponse
from rest_framework import status
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.core.files.storage import FileSystemStorage
from django.core.files import File

from .permissions import IsSeller, IsProductCardOwner
from .serializers import (ShopPricesUrlSerializer, ShopPricesSerializer, ShopStatusSerializer,
                          OrdersSerializer, OrdersItemSerializer, YamlErrorSerializer,
                          ImagesPostSerializer, ImagesDeleteSerializer)
from products.models import Category, ProductCard, Product, Parameter, ProductParameter
from buyer.models import Order, OrderPosition
from .models import Shop
from retail_order_api.docs_responses import (response_unauthorized, DetailResponseSerializer,
                                             IncorrectDataSerializer)
from .tasks import save_images, delete_images


responses_no_access = {**response_unauthorized,
                       status.HTTP_403_FORBIDDEN: OpenApiResponse(
                           response=DetailResponseSerializer,
                           description='The user is not a seller or '
                                       'the object does not belong to the seller'),
                       }


class SellerAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSeller, IsProductCardOwner]

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

            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
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


@extend_schema(tags=["shop"])
class OrdersView(SellerAPIView):

    @extend_schema(
        responses={status.HTTP_200_OK: OrdersSerializer(many=True),
                   **responses_no_access}
    )
    def get(self, request):
        orders = Order.objects.filter(positions__product_card__shop=self.user.shop).order_by('-created_at')
        serializer = OrdersSerializer(orders, many=True)
        return JsonResponse(serializer.data, safe=False)


@extend_schema(tags=["shop"])
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


@extend_schema(tags=["shop"])
class ProductCardImage(SellerAPIView):

    @extend_schema(
        request=ImagesPostSerializer,
        responses={status.HTTP_202_ACCEPTED: OpenApiResponse(description='Accepted.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Product card not found.'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **responses_no_access}
    )
    def post(self, request, product_card_id):
        try:
            product_card = ProductCard.objects.get(id=product_card_id)
        except ProductCard.DoesNotExist:
            return JsonResponse({'detail': 'The product card does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, obj=product_card)
        images = request.FILES.getlist('images')
        serializer = ImagesPostSerializer(data={'images': images})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        storage = FileSystemStorage()
        images_names = []
        for image in validated_data['images']:
            storage.save(image.name, File(image))
            images_names.append(image.name)
        save_images.delay(product_card_id, images_names)
        return HttpResponse(status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        request=ImagesDeleteSerializer,
        responses={status.HTTP_202_ACCEPTED: OpenApiResponse(description='Accepted.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Product card not found.'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **responses_no_access}
    )
    def delete(self, request, product_card_id):
        try:
            product_card = ProductCard.objects.get(id=product_card_id)
        except ProductCard.DoesNotExist:
            return JsonResponse({'detail': 'The product card does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, obj=product_card)
        serializer = ImagesDeleteSerializer(data=request.data, context={'product_card': product_card})
        serializer.is_valid(raise_exception=True)
        images_ids = [image.id for image in serializer.validated_data['images']]
        delete_images.delay(images_ids)
        return HttpResponse(status=status.HTTP_202_ACCEPTED)
