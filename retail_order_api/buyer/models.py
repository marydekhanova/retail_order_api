from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
from rest_framework import serializers

from products.models import ProductCard
from .exceptions import LimitError


User = get_user_model()

STATUS_CHOICES = (
    ('new', 'New'),
    ('confirmed', 'Confirmed'),
    ('assembled', 'Assembled'),
    ('sent', 'Sent'),
    ('delivered', 'Delivered'),
    ('canceled', 'Canceled'),
)


class CartPosition(models.Model):

    @property
    def price_per_quantity(self):
        return self.product_card.price * self.quantity

    product_card = models.ForeignKey(ProductCard, on_delete=models.CASCADE, related_name='users_carts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_positions')
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Cart's position"
        verbose_name_plural = "Cart's positions"
        constraints = [
            models.UniqueConstraint(fields=['user', 'product_card'], name='unique_cart_position'),
        ]


class TitleField(models.CharField):

    def get_prep_value(self, value):
        return str(value).capitalize()


class Address(models.Model):
    user = models.ForeignKey(User, related_name='addresses', on_delete=models.CASCADE)
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=15)
    building = models.CharField(max_length=15, blank=True, default='')
    apartment = models.CharField(max_length=15, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['city', 'street', 'house', 'building', 'apartment', 'user'], name='unique_address'),
        ]

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if not update_fields:
            active_addresses = self.user.addresses.all().filter(is_active=True)
            if self.is_active:
                if len(active_addresses) >= 5:
                    raise LimitError(f'No more than 5 addresses per user')
        super().save(*args, **kwargs)


class Order(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    first_name = TitleField(
        verbose_name='First name',
        max_length=40
    )
    middle_name = TitleField(
        verbose_name='Middle name',
        max_length=50,
        blank=True)
    last_name = TitleField(
        verbose_name='Last name',
        max_length=60
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name='Phone')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=9)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='orders')


class OrderPosition(models.Model):
    @property
    def price_per_quantity(self):
        return self.price * self.quantity

    product_card = models.ForeignKey(ProductCard, on_delete=models.CASCADE, related_name='orders')
    price = models.DecimalField(
        verbose_name='Price',
        max_digits=15,
        decimal_places=5,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='positions')
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Order's position"
        verbose_name_plural = "Order's positions"
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_card'], name='unique_order_position'),
        ]





