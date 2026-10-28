from django.db import models

# Create your models here.
import uuid

from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator


class PaymentCertificateModel(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("superseded", "Superseded"),
        ("cancelled", "Cancelled"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4,unique=True,editable=False,)
    certificate_number = models.CharField(max_length=50,blank=True)
    payment_claim = models.ForeignKey("claims.PaymentClaimModel",on_delete=models.PROTECT,related_name="certificates",)
    certified_amount = models.DecimalField(max_digits=12,decimal_places=2,null=True, blank=True)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="draft",)
    certification_date = models.DateField(null=True,blank=True,)
    expected_payment_date = models.DateField(null=True, blank=True)
    certifier = models.ForeignKey("authentication.UserModel",on_delete=models.SET_NULL,null=True,blank=True,related_name="issued_payment_certificates",)
    notes = models.TextField(blank=True,)
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True,)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["payment_claim", "certificate_number"],
                name="unique_claim_certificate_number",
            ),
            models.CheckConstraint(
                condition=models.Q(certified_amount__gte=0),
                name="certificate_amount_nonnegative",
            ),
        ]

    def __str__(self):
        return self.certificate_number