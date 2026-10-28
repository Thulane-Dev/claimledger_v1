from django.db import models
import uuid
from decimal import Decimal

# Import Models start
from account.models import *
from authentication.models import *
from projects.models import *

from django.core.validators import MinValueValidator

# =========================================================
# PAYMENT CLAIM
# =========================================================

class PaymentClaimModel(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("queried", "Queried"),
        ("resubmitted", "Resubmitted"),
        ("certified", "Certified"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]


    uuid = models.UUIDField(default=uuid.uuid4,unique=True,editable=False,)
    claim_number = models.CharField(max_length=50,blank=True)
    claim_title = models.CharField(max_length=50,blank=True)

    project = models.ForeignKey(
        ProjectModel,
        on_delete=models.PROTECT,null=True, blank=True,
        related_name="payment_claims",
    )

    claimant_company = models.ForeignKey(
        "account.CompanyModel",
        on_delete=models.PROTECT,null=True, blank=True,
        related_name="submitted_claims",
    )

    recipient_company = models.ForeignKey(
        "account.CompanyModel",
        on_delete=models.PROTECT,null=True, blank=True,
        related_name="received_claims",
    )

    claim_period_start = models.DateField(blank=True, null=True)
    claim_period_end = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    notes = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
            'authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="submitted_claims")

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["claimant_company", "claim_number"],
                name="unique_company_claim_number",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    claim_period_start__lte=models.F("claim_period_end")
                ),
                name="valid_claim_period",
            ),
        ]

    @property
    def total_amount(self):
        return self.line_items.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def total_paid(self):
        return self.payments.aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

    @property
    def outstanding_amount(self):
        return self.total_amount - self.total_paid

    def __str__(self):
        return self.claim_number


class PaymentClaimLineItemModel(models.Model):

    UNIT_CHOICES = [
        ("each", "Each"),
        ("box", "Box"),
        ("bag", "Bag"),
        ("tonne", "Tonne"),
        ("kg", "Kilogram (kg)"),
        ("m", "Metre (m)"),
        ("m2", "Square metre (m²)"),
        ("m3", "Cubic metre (m³)"),
        ("litre", "Litre"),
        ("hour", "Hour"),
        ("day", "Day"),
        ("load", "Load"),
        ("set", "Set"),
        ("roll", "Roll"),
        ("other", "Other"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payment_claim = models.ForeignKey("claims.PaymentClaimModel",on_delete=models.CASCADE,related_name="line_items",)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12,decimal_places=3,default=Decimal("1.000"),null=True, blank=True)
    unit = models.CharField(max_length=20,choices=UNIT_CHOICES,default="each",)
    custom_unit = models.CharField(max_length=50,blank=True,)
    rate = models.DecimalField(max_digits=12,decimal_places=2,default=Decimal("0.00"),null=True, blank=True)
    amount = models.DecimalField(max_digits=14,decimal_places=2,default=Decimal("0.00"),null=True, blank=True)
    certified_amount = models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True,default=None,)
    certification_notes = models.TextField(blank=True,
        help_text="Explain any difference between the claimed and certified amounts.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.amount = (
            self.quantity * self.rate
        ).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.description



class ClaimQueryModel(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("responded", "Responded"),
        ("resolved", "Resolved"),
        ("reopened", "Reopened"),
    ]

    TYPE_CHOICES = [
        ("query", "Query"),
        ("dispute", "Dispute"),
    ]


    uuid = models.UUIDField(default=uuid.uuid4,unique=True,editable=False,)
    claim_item = models.ForeignKey(PaymentClaimLineItemModel,on_delete=models.CASCADE,related_name="queries",null=True, blank=True,)
    reason = models.CharField(max_length=150,blank=True)
    dispute_amount = models.DecimalField(max_digits=12,decimal_places=2,null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="open",)
    type = models.CharField(max_length=20,choices=TYPE_CHOICES,default="query",)
    created_by_user = models.ForeignKey("authentication.UserModel",on_delete=models.SET_NULL,null=True,blank=True,related_name="created_claim_queries_user",)
    created_by_contractor = models.ForeignKey("account.CompanyModel",on_delete=models.PROTECT,null=True, blank=True,related_name="created_claim_queries_contractor",)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.reason


# Conversation messages belonging to a query.
class ClaimQueryResponseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4,unique=True,editable=False,)
    query = models.ForeignKey(ClaimQueryModel,on_delete=models.CASCADE,related_name="responses",null=True, blank=True,)
    message = models.TextField(blank=True)
    created_by_user = models.ForeignKey("authentication.UserModel",on_delete=models.SET_NULL,null=True, blank=True, related_name="claim_query_responses_user",)
    created_by_contractor = models.ForeignKey("account.CompanyModel",on_delete=models.PROTECT,null=True, blank=True,related_name="claim_query_responses_contractor",)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Response to {self.query_id}"

class QueriesResponsesAttachmentModel(models.Model):
    query = models.ForeignKey(
        "claims.ClaimQueryModel",
        on_delete=models.CASCADE,
        related_name="query_attachments",
        null=True,
        blank=True,
    )

    response = models.ForeignKey(
        "claims.ClaimQueryResponseModel",
        on_delete=models.CASCADE,
        related_name="response_attachments",
        null=True,
        blank=True,
    )
    photo = models.ImageField(upload_to="media/query_response_photos/", null=True, blank=True)
    file = models.FileField(upload_to="media/query_response_files/", null=True, blank=True,)
    original_filename = models.CharField(max_length=255)
    uploaded_by_user = models.ForeignKey('authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="query_responses_user_attachments")
    uploaded_by_contractor = models.ForeignKey('account.CompanyModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="query_responses_contactor_attachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_filename
    

class ClaimCertificationAttachmentModel(models.Model):
    line_item = models.ForeignKey("claims.PaymentClaimLineItemModel",on_delete=models.CASCADE,related_name="certification_attachments",)
    photo = models.ImageField(upload_to="media/certificate_photos/", null=True, blank=True)
    file = models.FileField(upload_to="media/certificate_files/", null=True, blank=True,)
    original_filename = models.CharField(max_length=255)
    uploaded_by_user = models.ForeignKey('authentication.UserModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="certificate_user_attachments")
    uploaded_by_contractor = models.ForeignKey('account.CompanyModel', null=True, blank=True, on_delete=models.SET_NULL, related_name="certificate_contactor_attachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_filename
