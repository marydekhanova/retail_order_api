from django.urls import re_path, path
from rest_framework.authtoken import views

from products.views import ProductList


app_name = 'products'
urlpatterns = [
    path('products/', ProductList.as_view(), name='products')
]