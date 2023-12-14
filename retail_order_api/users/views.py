from django.shortcuts import render
from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponse
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from rest_framework.authtoken.models import Token

from .serializers import (UserSerializer, UserUpdateSerializer,
                               PasswordSerializer, PasswordUpdateSerialize,
                               EmailUpdateSerialize)
from .signals import reset_password, update_email
from .permissions import IsAuthenticatedOrCreateOnly


User = get_user_model()


class UserView(APIView):
    permission_classes = [IsAuthenticatedOrCreateOnly]

    @property
    def user(self):
        return self.request.user

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        User.objects.create_user(**validated_data)
        return HttpResponse(status=status.HTTP_201_CREATED)

    def get(self, request):
        serializer = UserSerializer(self.user)
        return JsonResponse(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(instance=self.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        updated_user.save(update_fields=serializer.validated_data.keys())
        return JsonResponse(serializer.data)


class EmailConfirmation(APIView):

    def post(self, request):
        email = request.data.get('email')
        token = request.data.get('token')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': "Incorrect Email. User is not found."})
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            return JsonResponse({"detail": "Email confirmed."})
        else:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Invalid confirmation token.'})


class PasswordResetToken(APIView):

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': "Incorrect Email. User is not found."})
        reset_password.send(sender=self.__class__, user=user)
        return JsonResponse({"detail": f"Password reset token sent to {email}"})


class PasswordReset(APIView):

    def post(self, request):
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            user = User.objects.get(email=validated_data['email'])
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': "Incorrect Email. User is not found."})

        if default_token_generator.check_token(user, validated_data['token']):
            user.set_password(validated_data['new_password'])
            user.save()
            Token.objects.filter(user_id=user.id).delete()
            return JsonResponse({"detail": "Password updated."})
        else:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Invalid password reset token.'})


class PasswordUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordUpdateSerialize(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        user = request.user

        if not user.check_password(validated_data['current_password']):
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': "The current password is not correct."})

        user.set_password(validated_data['new_password'])
        user.save()
        Token.objects.filter(user_id=user.id).delete()
        return JsonResponse({"detail": "Password updated."})


class EmailUpdate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmailUpdateSerialize(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        user = request.user
        user.email = validated_data["email"]
        user.is_active = False
        user.save(update_fields=["email", "is_active"])
        Token.objects.filter(user_id=user.id).delete()
        update_email.send(sender=self.__class__, instance=user)
        return JsonResponse({"detail": f"Email confirmation token sent to {validated_data['email']}"})












