from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

from .models import User


class UserSerializer(serializers.ModelSerializer):
   password = serializers.CharField(validators=[validate_password], write_only=True)

   class Meta:
      model = User
      fields = (
         'id', 'last_name', 'first_name',
         'middle_name', 'company', 'job_title',
         'type', 'password', 'email',
      )
      read_only_fields = ('id',)


class UserUpdateSerializer(serializers.ModelSerializer):

   class Meta:
      model = User
      fields = (
         'last_name', 'first_name',
         'middle_name', 'company', 'job_title',
         'type'
      )

   def update(self, instance, validated_data):
      instance.last_name = validated_data.get('last_name', instance.last_name)
      instance.first_name = validated_data.get('first_name', instance.first_name)
      instance.middle_name = validated_data.get('middle_name', instance.middle_name)
      instance.company = validated_data.get('company', instance.company)
      instance.job_title = validated_data.get('job_title', instance.job_title)
      instance.type = validated_data.get('type', instance.type)
      return instance


class PasswordResetTokenSerializer(serializers.Serializer):
   email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
   new_password = serializers.CharField(validators=[validate_password], write_only=True)
   email = serializers.EmailField()
   token = serializers.CharField()


class PasswordUpdateSerialize(serializers.Serializer):
   current_password = serializers.CharField()
   new_password = serializers.CharField(validators=[validate_password], write_only=True)
   re_new_password = serializers.CharField()

   def validate(self, data):
      if data['new_password'] != data['re_new_password']:
         raise serializers.ValidationError("Passwords for update do not match.")
      return data


class EmailUpdateSerialize(serializers.ModelSerializer):

   class Meta:
      model = User
      fields = ('email',)


class EmailConfirmationSerialize(serializers.Serializer):
   email = serializers.EmailField()
   token = serializers.CharField()


class AuthTokenSerializer(serializers.Serializer):
   email = serializers.CharField(
      write_only=True
   )
   password = serializers.CharField(
      style={'input_type': 'password'},
      trim_whitespace=False,
      write_only=True
   )
   token = serializers.CharField(
      read_only=True
   )

   def validate(self, attrs):
      email = attrs.get('email')
      password = attrs.get('password')

      if email and password:
         user = authenticate(request=self.context.get('request'),
                             email=email, password=password)

         # The authenticate call simply returns None for is_active=False
         # users. (Assuming the default ModelBackend authentication
         # backend.)
         if not user:
            msg = _('Unable to log in with provided credentials.')
            raise serializers.ValidationError(msg, code='authorization')
      else:
         msg = _('Must include "email" and "password".')
         raise serializers.ValidationError(msg, code='authorization')

      attrs['user'] = user
      return attrs


class ObtainAuthTokenSerializer(serializers.Serializer):
   token = serializers.CharField()

