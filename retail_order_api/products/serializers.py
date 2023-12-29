from rest_framework import serializers

from products.models import ProductCard, ProductParameter


class ParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')

class ProductSerializer(serializers.ModelSerializer):
    name = serializers.StringRelatedField(source='product')
    parameters = ParameterSerializer(many=True)

    class Meta:
        model = ProductCard
        fields = ('id', 'name', 'description', 'shop', 'parameters', 'price', 'quantity', 'images')
