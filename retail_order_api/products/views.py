from rest_framework import generics

from .models import ProductCard
from .serializers import ProductSerializer


class ProductList(generics.ListAPIView):
    queryset = ProductCard.objects.all().filter(status='in_stock', shop__open_for_orders=True)
    serializer_class = ProductSerializer
    filterset_fields = ['category', 'shop']




