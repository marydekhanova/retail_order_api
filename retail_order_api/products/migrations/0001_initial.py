# Generated by Django 4.2.7 on 2023-12-14 07:56

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.PositiveIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=40, verbose_name='Name')),
            ],
            options={
                'verbose_name': 'Parameter name',
                'verbose_name_plural': 'Parameter names',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
            ],
            options={
                'verbose_name': 'Product',
                'verbose_name_plural': 'Products',
                'ordering': ('-name',),
            },
        ),
        migrations.CreateModel(
            name='ProductCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_code', models.PositiveIntegerField()),
                ('model', models.CharField(blank=True, max_length=80)),
                ('description', models.TextField(blank=True, null=True)),
                ('price', models.DecimalField(decimal_places=5, max_digits=15, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('price_rrc', models.DecimalField(decimal_places=5, max_digits=15, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('quantity', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('in_stock', 'In_stock'), ('sold', 'Sold'), ('withdrawn', 'Withdrawn')], default='in_stock')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_cards', to='products.product')),
            ],
            options={
                'verbose_name': 'Product card',
                'verbose_name_plural': 'Product cards',
            },
        ),
        migrations.CreateModel(
            name='ProductParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(max_length=100)),
                ('parameter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='products.parameter')),
                ('product_card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='products.productcard')),
            ],
            options={
                'verbose_name': 'Product parameter',
                'verbose_name_plural': 'Product parameters',
            },
        ),
    ]
