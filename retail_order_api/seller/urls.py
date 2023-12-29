from django.urls import path, include
from rest_framework.authtoken import views

from .views import ShopPrices, ShopStatus, OrdersView, OrdersItemView, ProductCardImage


app_name = 'seller'
urlpatterns = [
    path('shop/prices/', ShopPrices.as_view(), name='shop_prices'),
    path('shop/status/', ShopStatus.as_view(), name='shop_status'),
    path('shop/orders/', OrdersView.as_view(), name='orders'),
    path('shop/orders/<int:order_id>/', OrdersItemView.as_view(), name='order'),
    path('shop/product_card/<int:product_card_id>/images/', ProductCardImage.as_view(), name='product_card_image')
]
