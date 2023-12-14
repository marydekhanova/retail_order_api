from django.urls import path, include
from rest_framework.authtoken import views

from .views import ShopPrice, ShopStatus, OrdersView, OrdersItemView


app_name = 'seller'
urlpatterns = [
    path('shop/price/', ShopPrice.as_view(), name='shop_price'),
    path('shop/status/', ShopStatus.as_view(), name='shop_status'),
    path('orders/', OrdersView.as_view(), name='orders'),
    path('orders/<int:order_id>/', OrdersItemView.as_view(), name='order')
]