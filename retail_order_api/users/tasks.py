from django.core.mail import EmailMultiAlternatives
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives


User = get_user_model()


@shared_task()
def send_confirmation_token_to_email_task(user_id):
    user = User.objects.get(id=user_id)
    print(user)
    token = default_token_generator.make_token(user)
    msg = EmailMultiAlternatives(
        f"Подтверждение почты",
        f"Токен для подтверждения почты {token}",
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg.send()


@shared_task()
def send_reset_password_token_to_email_task(user_id):
    user = User.objects.get(id=user_id)
    token = default_token_generator.make_token(user)
    msg = EmailMultiAlternatives(
        f"Cброс пароля",
        f"Токен для сброса пароля {token}",
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg.send()