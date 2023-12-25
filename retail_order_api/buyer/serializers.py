from rest_framework import serializers
from decimal import Decimal

from .models import CartPosition, Address, Order, OrderPosition
from products.models import ProductCard, Product


class CartPositionSerializer(serializers.ModelSerializer):
    price_per_quantity = serializers.DecimalField(max_digits=15, decimal_places=2,
                                                  min_value=Decimal('0.00'), read_only=True)

    class Meta:
        model = CartPosition
        fields = ('product_card', 'quantity', 'price_per_quantity',)


    def validate_product_card(self, value):
        if value.status == 'sold' or value.status == 'withdrawn':
            raise serializers.ValidationError(f"The product is sold or withdrawn.")
        return value

    def validate(self, data):
        if (data['product_card'].quantity - data['quantity']) < 0:
            raise serializers.ValidationError(f"Quantity exceeds the actual stock of the product.")
        return data


class CartSerializer(serializers.Serializer):
    unvailable_positions = CartPositionSerializer(many=True)
    available_positions = CartPositionSerializer(many=True)
    total = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal('0.00'))


class CartPositionDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = CartPosition
        fields = ('product_card',)


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = ('id', 'city', 'street', 'house', 'building', 'apartment')
        fiels_read_only = ('id',)

    def update(self, instance, validated_data):
        instance.city = validated_data.get('city', instance.city)
        instance.street = validated_data.get('street', instance.street)
        instance.house = validated_data.get('house', instance.house)
        instance.building = validated_data.get('building', instance.building)
        instance.apartment = validated_data.get('apartment', instance.apartment)
        return instance


class OrderPositionSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(source='product_card.product')
    shop = serializers.StringRelatedField(source='product_card.shop')

    class Meta:
        model = OrderPosition
        fields = ('product', 'shop', 'price', 'quantity', 'price_per_quantity')


class OrderSerializer(serializers.ModelSerializer):
    address = AddressSerializer()
    positions = OrderPositionSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    delivered_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'created_at', 'updated_at', 'delivered_at',
                  'status', 'first_name', 'last_name',
                  'middle_name', 'email', 'phone', 'address', 'positions')
        read_only_fields = ('id', 'created_at', 'positions', 'created_at', 'updated_at', 'status')


class OrderListSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = Order
        fields = ('id', 'created_at', 'status',)


class OrderNewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id',)






















