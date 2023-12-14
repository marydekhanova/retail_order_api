from django.dispatch import receiver
from django.db.models.signals import post_save
from django.dispatch import Signal
from django.conf import settings

from .tasks import (send_confirmation_token_to_email_task,
                    send_reset_password_token_to_email_task)


update_email = Signal()


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="post_save_user")
def send_confirmation_token_to_email(sender, instance, created, **kwargs):
    user_id = instance.id
    if created:
        send_confirmation_token_to_email_task.delay(user_id)


@receiver(update_email, dispatch_uid="update_email")
def send_confirmation_token_to_new_email(sender, instance, **kwargs):
    user_id = instance.id
    send_confirmation_token_to_email_task.delay(user_id)


reset_password = Signal()


@receiver(reset_password)
def send_reset_password_token_to_email(user, **kwargs):
    send_reset_password_token_to_email_task.delay(user.id)




