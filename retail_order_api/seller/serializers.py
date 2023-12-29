from rest_framework import serializers
import requests

from products.models import Category, ProductCard, Image
from buyer.models import OrderPosition, Order, Address
from .models import Shop

class ShopPricesUrlSerializer(serializers.Serializer):
    url = serializers.URLField()


class CategorySerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=80)

    def validate(self, data):
        try:
            category = Category.objects.get(name=data['name'])
            if category.id != data['id']:
                raise serializers.ValidationError(f"Category '{category.name}' already exists with '{category.id}' id.")
        except Category.DoesNotExist:
            pass
        return data


class GoodSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(min_value=1)
    category = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=80)
    parameters = serializers.DictField(child=serializers.CharField(), allow_empty=True, required=False)

    class Meta:
        model = ProductCard
        fields = ('id', 'category', 'model', 'name', 'price', 'price_rrc', 'quantity', 'parameters')


class ShopPricesSerializer(serializers.Serializer):
    shop = serializers.CharField()
    categories = CategorySerializer(many=True)
    goods = GoodSerializer(many=True)

    def validate(self, data):
        categories_id = [category['id'] for category in data['categories']]
        for good in data['goods']:
            if good['category'] not in categories_id:
                raise serializers.ValidationError(f"Good's categories must correspond to the listed categories.")
        return data


class ShopStatusSerializer(serializers.ModelSerializer):
    open_for_orders = serializers.BooleanField()

    class Meta:
        model = Shop
        fields = ('open_for_orders', )


class OrdersSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'created_at')


class OrderPositionSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(source='product_card.product')

    class Meta:
        model = OrderPosition
        fields = ('id', 'product', 'quantity', 'price_per_quantity')


class OrdersItemSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    items = OrderPositionSerializer(source='seller_positions', many=True)

    class Meta:
        model = Order
        fields = ('id', 'created_at', 'status', 'items')


class YamlErrorSerializer(serializers.Serializer):
    yaml_error = serializers.CharField()


class ImagesPostSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField(), min_length=1, max_length=6)


class ImagesDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCard
        fields = ('images',)

    def validate_images(self, images):
        product_card = self.context['product_card']
        for image in images:
            if image.product_card != product_card:
                raise serializers.ValidationError(
                    f"The image with id '{image.id}' does not belong to the product card")
        return images
