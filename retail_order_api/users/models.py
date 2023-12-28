from django.contrib.auth import models
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django_cleanup import cleanup
from easy_thumbnails.fields import ThumbnailerImageField


USER_TYPE_CHOICES = (
    ('seller', 'Seller'),
    ('buyer', 'Buyer'),
)


class TitleField(models.CharField):

    def get_prep_value(self, value):
        return str(value).capitalize()


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError('The given email must be set.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields['is_staff'] = True
        extra_fields['is_superuser'] = True
        return self._create_user(email, password, **extra_fields)


@cleanup.select
class User(AbstractUser):
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    first_name = TitleField(verbose_name='First name',
                            max_length=40)
    middle_name = TitleField(verbose_name='Middle name',
                             max_length=50,
                             blank=True)
    last_name = TitleField(verbose_name='Last name',
                           max_length=60)
    username = None
    avatar = ThumbnailerImageField(verbose_name="Avatar", upload_to='users/avatars',
                                   resize_source=dict(quality=100, size=(50, 50), sharpen=True),
                                   blank=True)
    email = models.EmailField(unique=True)
    company = models.CharField(verbose_name='Company', max_length=40, blank=True)
    job_title = models.CharField(verbose_name='Job title', max_length=40, blank=True)
    type = models.CharField(verbose_name='User type',
                            choices=USER_TYPE_CHOICES,
                            default='buyer')
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ('email',)
