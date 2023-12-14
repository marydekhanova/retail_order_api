# Generated by Django 4.2.7 on 2023-12-14 07:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
        ('buyer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderposition',
            name='product_card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='products.productcard'),
        ),
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='buyer.address'),
        ),
    ]