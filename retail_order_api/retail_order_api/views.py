from django.http import JsonResponse
from rest_framework import status


def pageNotFound(request, exception):
    return JsonResponse({'detail': 'Page not found.'},
                        status=status.HTTP_404_NOT_FOUND)