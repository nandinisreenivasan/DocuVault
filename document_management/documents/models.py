from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

import uuid

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ('ID Card', 'ID Card'),
        ('IRS Form', 'IRS Form'),
        ('Passport', 'Passport'),
        ('Bank Statement', 'Bank Statement'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pages = models.IntegerField()
    text = models.TextField()
    tags = models.JSONField()
    doc_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")

    def __str__(self):
        return f"{self.doc_type} - {self.id} ({self.uploaded_by.email})"
