from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Shop(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(null=True, blank=True)
    user = models.OneToOneField(User, related_name='shop', on_delete=models.CASCADE)
    open_for_orders = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Shop'
        verbose_name_plural = "Shops"
        ordering = ('-name',)

    def __str__(self):
        return self.name