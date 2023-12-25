from rest_framework.views import APIView
from django.http import JsonResponse, HttpResponse
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework import status, parsers, renderers
from django.contrib.auth.tokens import default_token_generator
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.compat import coreapi, coreschema
from rest_framework.schemas import coreapi as coreapi_schema
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken

from .serializers import (UserSerializer, UserUpdateSerializer,
                          PasswordResetTokenSerializer, PasswordResetSerializer,
                          PasswordUpdateSerialize, EmailUpdateSerialize,
                          EmailConfirmationSerialize, AuthTokenSerializer,
                          ObtainAuthTokenSerializer)
from .signals import reset_password, update_email
from .permissions import IsAuthenticatedOrCreateOnly
from retail_order_api.docs_responses import (response_unauthorized, DetailResponseSerializer,
                                             IncorrectDataSerializer)


User = get_user_model()


@extend_schema(tags=["user"])
class UserView(APIView):
    permission_classes = [IsAuthenticatedOrCreateOnly]

    @property
    def user(self):
        return self.request.user

    @extend_schema(
        request=UserSerializer,
        responses={status.HTTP_201_CREATED: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **response_unauthorized}
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        User.objects.create_user(**validated_data)
        return HttpResponse(status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={status.HTTP_200_OK: UserSerializer,
                   **response_unauthorized}
    )
    def get(self, request):
        serializer = UserSerializer(self.user)
        return JsonResponse(serializer.data)

    @extend_schema(
        request=UserUpdateSerializer,
        responses={status.HTTP_200_OK: UserUpdateSerializer,
                   **response_unauthorized}
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(instance=self.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        updated_user.save(update_fields=serializer.validated_data.keys())
        return JsonResponse(serializer.data)


@extend_schema(tags=["user"])
class EmailConfirmation(APIView):

    @extend_schema(
        request=EmailConfirmationSerialize,
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                                description='Incorrect Email. User is not found.')}
    )
    def post(self, request):
        serialize = EmailConfirmationSerialize(data=request.data)
        serialize.is_valid(raise_exception=True)
        validated_data = serialize.validated_data
        try:
            user = User.objects.get(email=validated_data['email'])
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_404_NOT_FOUND,
                data={'detail': "Incorrect Email. User is not found."})
        if default_token_generator.check_token(user, validated_data['token']):
            user.is_active = True
            user.save(update_fields=["is_active"])
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'token': 'Invalid confirmation token.'})


@extend_schema(tags=["user"])
class PasswordResetToken(APIView):

    @extend_schema(
        request=PasswordResetTokenSerializer,
        responses={status.HTTP_200_OK: OpenApiResponse(response=DetailResponseSerializer),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                                description='Incorrect Email. User is not found.')}
    )
    def post(self, request):
        serializer = PasswordResetTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        email = validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_404_NOT_FOUND,
                data={'detail': "Incorrect Email. User is not found."})
        reset_password.send(sender=self.__class__, user=user)
        return JsonResponse({"detail": f"Password reset token sent to {email}"})


@extend_schema(tags=["user"])
class PasswordReset(APIView):

    @extend_schema(
        request=PasswordResetSerializer,
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   status.HTTP_404_NOT_FOUND: OpenApiResponse(response=DetailResponseSerializer,
                                                              description='Incorrect Email. User is not found.')}
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        try:
            user = User.objects.get(email=validated_data['email'])
        except User.DoesNotExist:
            return JsonResponse(
                status=status.HTTP_404_NOT_FOUND,
                data={'detail': "Incorrect Email. User is not found."})
        if default_token_generator.check_token(user, validated_data['token']):
            user.set_password(validated_data['new_password'])
            user.save()
            Token.objects.filter(user_id=user.id).delete()
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        else:
            return JsonResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data={'detail': 'Invalid password reset token.'})


@extend_schema(tags=["user"])
class PasswordUpdate(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PasswordUpdateSerialize,
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **response_unauthorized}
    )
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
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["user"])
class EmailUpdate(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EmailUpdateSerialize,
        responses={status.HTTP_200_OK: OpenApiResponse(response=DetailResponseSerializer),
                   status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                description='Incorrect data.'),
                   **response_unauthorized}
    )
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


@extend_schema(tags=["user"])
class CustomObtainAuthToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer

    @extend_schema(
            responses={status.HTTP_200_OK: OpenApiResponse(response=ObtainAuthTokenSerializer),
                       status.HTTP_400_BAD_REQUEST: OpenApiResponse(response=IncorrectDataSerializer,
                                                                    description='Incorrect data.')}
        )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["user"])
class DeleteAuthToken(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={status.HTTP_204_NO_CONTENT: OpenApiResponse(description='OK'),
                   **response_unauthorized}
    )
    def delete(self, request):
        Token.objects.filter(user=request.user).delete()
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)









