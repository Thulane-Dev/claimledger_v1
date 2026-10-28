from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Sum,Prefetch
from decimal import Decimal, InvalidOperation
from datetime import date,datetime

# htmx
from django.http import HttpResponse
import json

# Models Import
from .models import *
from authentication.models import *
from claims.models import *

# ============= ALL CERTIFICATES VIEW =============
def CertificatesView(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    context = {
        "current_user" : current_user,
        "page": "certificates/certificates.html",
    }

    if request.htmx:
        return render(request, "certificates/certificates.html", context)
    return render(request, "client/base.html", context)


# ============= CREATE CERTIFICATE VIEW =============
def CreateCertificateView(request, claim_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    payment_claim = get_object_or_404(
        PaymentClaimModel,
        uuid=claim_uuid,
    )

    line_items = payment_claim.line_items.all().order_by("sort_order", "created_at")

    for line_item in line_items:
        line_item.certification_difference = None

        if line_item.certified_amount is not None:
            line_item.certification_difference = (
                (line_item.amount or Decimal("0.00"))
                - line_item.certified_amount
            )

    claimed_total = sum(
        (line_item.amount or Decimal("0.00") for line_item in line_items),
        Decimal("0.00"),
    )

    certified_subtotal = sum(
        (
            line_item.certified_amount or Decimal("0.00")
            for line_item in line_items
        ),
        Decimal("0.00"),
    )

    # SAMPLE DATA ONLY.
    # Replace this with records from a real certificate deduction model.
    sample_deductions = [
        {
            "name": "Retention",
            "category": "retention",
            "description": "5% retention withheld",
            "amount": Decimal("2500.00"),
        },
        {
            "name": "Penalties",
            "category": "penalty",
            "description": "Delay penalty",
            "amount": Decimal("500.00"),
        },
        {
            "name": "Previous payment adjustment",
            "category": "adjustment",
            "description": "Adjustment for previous certification",
            "amount": Decimal("750.00"),
        },
    ]

    sample_deduction_total = sum(
        (deduction["amount"] for deduction in sample_deductions),
        Decimal("0.00"),
    )

    context = {
        "current_user": current_user,
        "company": company,
        "payment_claim": payment_claim,
        "line_items": line_items,
        "claimed_total": claimed_total,
        "certified_subtotal": certified_subtotal,
        "sample_deductions": sample_deductions,
        "sample_deduction_total": sample_deduction_total,
        "sample_net_payable": certified_subtotal - sample_deduction_total,
        "page": "certificates/create_certificate.html",
    }

    if request.htmx:
        return render(
            request,
            "certificates/create_certificate.html",
            context,
        )

    return render(request, "client/base.html", context)
