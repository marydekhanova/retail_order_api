# Generated by Django 4.2.7 on 2023-12-14 07:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('buyer', '0002_initial'),
        ('products', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='cartposition',
            name='product_card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users_carts', to='products.productcard'),
        ),
        migrations.AddField(
            model_name='cartposition',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_positions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='address',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='orderposition',
            constraint=models.UniqueConstraint(fields=('order', 'product_card'), name='unique_order_position'),
        ),
        migrations.AddConstraint(
            model_name='cartposition',
            constraint=models.UniqueConstraint(fields=('user', 'product_card'), name='unique_cart_position'),
        ),
        migrations.AddConstraint(
            model_name='address',
            constraint=models.UniqueConstraint(fields=('city', 'street', 'house', 'building', 'apartment', 'user'), name='unique_address'),
        ),
    ]
