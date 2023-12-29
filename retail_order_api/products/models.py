from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from easy_thumbnails.fields import ThumbnailerImageField
from django_cleanup import cleanup

from seller.models import Shop


STATUS_CHOICES = (
    ('in_stock', 'In_stock'),
    ('sold', 'Sold'),
    ('withdrawn', 'Withdrawn'),
)


class Category(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    shops = models.ManyToManyField(
        Shop,
        related_name='categories',
        blank=True
    )

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = "Categories"
        ordering = ('-name',)
        constraints = [
            models.UniqueConstraint(
                fields=['id', 'name'],
                name='unique_id_name_pair'
            ),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=80, unique=True)
    category = models.ForeignKey(
        Category,
        related_name='products',
        blank=True,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = "Products"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductCard(models.Model):
    product_code = models.PositiveIntegerField()
    model = models.CharField(max_length=80, blank=True)
    product = models.ForeignKey(
        Product,
        related_name='product_cards',
        on_delete=models.CASCADE
    )
    description = models.TextField(blank=True, null=True)
    shop = models.ForeignKey(
        Shop,
        related_name='product_cards',
        on_delete=models.CASCADE
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    price_rrc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(choices=STATUS_CHOICES, default='in_stock')

    class Meta:
        verbose_name = 'Product card'
        verbose_name_plural = "Product cards"
        constraints = [
            models.UniqueConstraint(
                fields=['product_code', 'product', 'shop'],
                name='unique_product_card'
            ),
        ]


class Parameter(models.Model):
    name = models.CharField(max_length=40, verbose_name='Name')

    class Meta:
        verbose_name = 'Parameter name'
        verbose_name_plural = "Parameter names"
        ordering = ('-name',)

    def __str__(self):
        return self.name


def get_upload_path(instance, filename):
    return 'shop_{0}/{1}'.format(instance.product_card.shop.id, filename)


@cleanup.select
class Image(models.Model):
    product_card = models.ForeignKey(ProductCard,
                                     related_name='images',
                                     on_delete=models.CASCADE)
    image = ThumbnailerImageField(upload_to=get_upload_path)


class ProductParameter(models.Model):
    product_card = models.ForeignKey(ProductCard,
                                     related_name='parameters',
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, related_name='products',
                                  on_delete=models.CASCADE)
    value = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Product parameter'
        verbose_name_plural = "Product parameters"
        constraints = [
            models.UniqueConstraint(fields=['product_card', 'parameter'], name='unique_product_parameter'),
        ]