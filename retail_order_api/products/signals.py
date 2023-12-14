from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.conf import settings
from django.dispatch import Signal

from .models import ProductCard


@receiver(pre_save, sender=ProductCard, dispatch_uid="pre_save_product")
def pre_save_product(sender, instance, update_fields, **kwargs):
    if instance.status != 'withdrawn':
        if instance.quantity == 0:
            instance.status = 'sold'
        else:
            instance.status = 'in_stock'
    return instance


