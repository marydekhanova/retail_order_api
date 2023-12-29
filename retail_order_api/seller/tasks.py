from celery import shared_task
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from pathlib import Path

from products.models import Image, ProductCard


@shared_task()
def save_images(product_card_id, images_names):
    product_card = ProductCard.objects.get(id=product_card_id)
    storage = FileSystemStorage()
    images_objects = []
    for image_name in images_names:
        path = storage.path(image_name)
        path_object = Path(path)
        with path_object.open(mode='rb') as file:
            image = File(file, name=f'{product_card_id}_{image_name}')
            image_object = Image(product_card=product_card, image=image)
            image_object.save()
            images_objects.append(image_object)
            storage.delete(image_name)


@shared_task()
def delete_images(images_ids):
    for image_id in images_ids:
        Image.objects.get(id=image_id).delete()
