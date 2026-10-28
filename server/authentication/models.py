from django.db import models
from django.contrib.auth.models import User
from account.models import *
from django.core.validators import EmailValidator
from django.utils.timezone import now
from datetime import timedelta
import os
import uuid
from account.models import AddressModel, CompanyModel


def default_end_date():
    return now().date() + timedelta(days=30)


# Create your models here.
class UserModel(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('de-active', 'De-Active'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(
        User, null=True, on_delete=models.CASCADE, unique=True)
    company = models.ForeignKey(
        CompanyModel, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=200, null=True, blank=True)
    last_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20, null=True, blank=True)
    account_complete = models.BooleanField(default=False)
    agreeTerms = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(default=now)
    end_date = models.DateField(default=default_end_date)
    address = models.ForeignKey(
        AddressModel, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='admin')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    date_created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.first_name} - {self.last_name}"


    

