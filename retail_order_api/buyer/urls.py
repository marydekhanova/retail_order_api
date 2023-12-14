from django.urls import path
from rest_framework.authtoken import views

from .views import CartView, CartPositionView, OrdersView, OrderView, AddressesView, AddressView


app_name = 'buyer'
urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/position/', CartPositionView.as_view(), name='cart_position'),
    path('orders/', OrdersView.as_view(), name='orders'),
    path('orders/<int:pk>/', OrderView.as_view(), name='order_detail'),
    path('addresses/', AddressesView.as_view(), name='addresses'),
    path('addresses/<int:pk>/', AddressView.as_view(), name='address')
]