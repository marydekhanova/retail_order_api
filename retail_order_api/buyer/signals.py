from django.dispatch import receiver
from django.dispatch import Signal
from django.conf import settings

from .tasks import send_invoice_to_email_task


new_order = Signal()


@receiver(new_order, dispatch_uid="new_order")
def send_invoice_to_email(order, buyer_email, **kwargs):
    order_id = order.id
    send_invoice_to_email_task.delay(order_id, buyer_email)







