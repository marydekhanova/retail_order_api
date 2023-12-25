from rest_framework import status
from rest_framework import serializers
from drf_spectacular.utils import OpenApiResponse


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


response_unauthorized = {
    status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
        response=DetailResponseSerializer,
        description='Authentication credentials were not provided '
                    'or invalid token.'),
}


class IncorrectDataSerializer(serializers.Serializer):
    field_name = serializers.ListField()
