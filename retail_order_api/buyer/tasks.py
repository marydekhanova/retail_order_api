from django.core.mail import EmailMultiAlternatives
from celery import shared_task
from django.conf import settings


@shared_task()
def send_invoice_to_email_task(order_id, buyer_email):
    msg = EmailMultiAlternatives(
        f"Заказ {order_id}",
        f"Накладная по заказу {order_id}",
        settings.EMAIL_HOST_USER,
        [buyer_email]
    )
    msg.send()