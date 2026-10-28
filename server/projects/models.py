from django.db import models
import uuid


# Import Models start
from account.models import *
from authentication.models import *

# Create your models here.
class ProjectModel(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("on_hold", "On hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    company = models.ForeignKey(
        CompanyModel, on_delete=models.CASCADE, null=True, blank=True, related_name="projects")
    project_name = models.CharField(max_length=255, blank=True)
    site_reference = models.CharField(max_length=255, blank=True)

    client_contact_name = models.CharField(max_length=255, blank=True)
    client_contact_email = models.EmailField(blank=True)
    client_contact_phone = models.CharField(max_length=32, blank=True)


    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(null=True, blank=True)

    location = models.ForeignKey(
        AddressModel, on_delete=models.CASCADE, null=True, blank=True)
    latitude = models.CharField(max_length=255, blank=True)
    longitude = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    
    cover_image = models.ImageField(
        upload_to="media/project_images/", null=True, blank=True)
    
    created_by = models.ForeignKey(
            'authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="created_by_user")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project_name} - {self.company.name}"





