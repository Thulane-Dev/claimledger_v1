from django.db import models
import uuid


# Create your models here.
class AddressModel(models.Model):
    PROVINCE_CHOICES = [
        ('EC', 'Eastern Cape'),
        ('FS', 'Free State'),
        ('GP', 'Gauteng'),
        ('KZN', 'KwaZulu-Natal'),
        ('LP', 'Limpopo'),
        ('MP', 'Mpumalanga'),
        ('NC', 'Northern Cape'),
        ('NW', 'North West'),
        ('WC', 'Western Cape'),
    ]
    
    street = models.CharField(max_length=255,blank=True,)  # Street address usually required
    suburb = models.CharField(max_length=255, blank=True, null=True)  # Added suburb field
    city = models.CharField(max_length=255, blank=True, null=True)
    province = models.CharField(max_length=10, choices=PROVINCE_CHOICES, blank=True, null=True)
    postal_code = models.CharField(max_length=4,blank=True,)  # Limited to 4 digits
    country = models.CharField(max_length=255, default='South Africa')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.street} - {self.city} {self.province}"


class CompanyModel(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('de-active', 'De-Active'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, blank=True)
    address = models.ForeignKey(
            AddressModel, on_delete=models.CASCADE, null=True, blank=True)
    registration_number = models.CharField(max_length=64, blank=True)
    vat_number = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    owner = models.ForeignKey(
           'authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL,related_name="company_owner")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
            return f"{self.name}"



class AttachmentsModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    project = models.ForeignKey('projects.ProjectModel', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='project_attachments')
    reference = models.CharField(max_length=255, blank=True,)
    photo = models.ImageField(
        upload_to="media/project_photos/", null=True, blank=True)
    file = models.FileField(
        upload_to="media/project_files/", null=True, blank=True,)
    caption = models.TextField(blank=True)
    payment_claim_attachments = models.ForeignKey("claims.PaymentClaimModel",null=True,blank=True,on_delete=models.CASCADE,related_name="payment_claim_attachments",)
    claimLineItem_attachments = models.ForeignKey("claims.PaymentClaimLineItemModel",null=True,blank=True,on_delete=models.CASCADE,related_name="claimLineItem_attachments",)
    uploaded_by_user = models.ForeignKey(
        'authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="user_attachments")
    uploaded_by_contractor = models.ForeignKey(
            'account.CompanyModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="contactor_attachments")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def filesize(self):
        uploaded_file = self.photo or self.file

        if not uploaded_file:
            return ""

        size = uploaded_file.size

        if size < 1024:
            return f"{size} B"

        if size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"

        if size < 1024 ** 3:
            return f"{size / (1024 ** 2):.1f} MB"

        return f"{size / (1024 ** 3):.1f} GB"

    def __str__(self):
        return f"{self.caption}"
