from django.urls import path, include
from rest_framework.authtoken import views

from .views import (UserView, EmailConfirmation,
                    PasswordResetToken, PasswordReset,
                    PasswordUpdate, EmailUpdate, CustomObtainAuthToken,
                    DeleteAuthToken, AvatarView, AvatarDeleteView)


app_name = 'users'
urlpatterns = [
    path('token/obtain/', CustomObtainAuthToken.as_view(), name='token_obtain'),
    path('token/delete/', DeleteAuthToken.as_view(), name='token_delete'),
    path('email/confirmation/', EmailConfirmation.as_view(), name='email_confirmation'),
    path('', UserView.as_view(), name='user'),
    path('password/reset/token/', PasswordResetToken.as_view(), name='password_reset_token'),
    path('password/reset/', PasswordReset.as_view(), name='password_reset'),
    path('password/update/', PasswordUpdate.as_view(), name='password_update'),
    path('email/update/', EmailUpdate.as_view(), name='email_update'),
    path('avatar/', AvatarView.as_view(), name='avatar'),
    path('avatar/', AvatarDeleteView.as_view(), name='avatar_delete'),

]
