"""A User model that uses the email field as a login

This is an example file that is not used or imported by default. It shows how to
create a User model that uses email addresses as the login field.

It includes a custom UserManager that tweaks the createsuperuser management
command, and also a case insensitive email field.

If you wish to use this model, you should copy it over into your models file and
replace your existing User model. Then make and run migrations. Or if this is
your initial migration, delete it and re-create it.

NOTE: On postgres you must run "CREATE EXTENSION CITEXT" before the
initial migration to enable the citext extension.
"""

from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext_lazy as _

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class CICharField(models.CharField):
    """Case insensitive char field

    Uses the database native case insensitivity functionality.

    Currently supports only sqlite and postgres. Note the respective caveats
    for each database type (such as sqlite only normalizing characters in the
    ASCII range) but for a lot of applications, this should work just fine.

    Preserves case, but comparisons and indexes on this field are case
    insensitive compares.
    """
    def db_type(self, connection):
        if connection.vendor == "sqlite":
            return super().db_type(connection) + " COLLATE NOCASE"

        elif connection.vendor == "postgresql":
            return "CITEXT"

        return None

class CIEmailField(CICharField, models.EmailField):
    """Case insensitive email field

    Email addresses are officially case sensitive except for the domain part,
    but many providers decide to make the user part insensitive. So this field
    is handy when you want to allow case insensitive email address matching
    (for example, for a username field), while preserving case so emails
    actually sent will be delivered correctly to providers that are case
    sensitive.

    The downside for using this as a login field is that two users who
    legitimately have different email addresses differing only by case will
    not be able to both have accounts. That's probably rare, however,
    and something we may want to disallow anyways.
    """
    pass

class User(AbstractUser):
    """User model that uses email address as the identifier"""
    username = None
    email = CIEmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

# The following is a custom admin model. This should really go in the
# admin.py file but for the sake of keeping the email-user model all in one
# file, it's included inline here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
import django.contrib.auth.models

admin.site.unregister(django.contrib.auth.models.Group)

@admin.register(User)
class UserAdmin(UserAdmin):
    fieldsets = [
        (None, {'fields': ["email", "password"]}),
        ("Personal Info", {"fields": ["first_name", "last_name"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser"]}),
        ("Important dates", {"fields": ["last_login", "date_joined"]})
    ]

    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_staff"]
    add_fieldsets = [
        (None, {
            'classes': ["wide"],
            'fields': ["email", "password1", "password2"]
        })
    ]
