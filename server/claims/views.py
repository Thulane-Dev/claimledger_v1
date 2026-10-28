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


# ============= CREATE CLAIM VIEW =============
def CreatePaymentClaimView(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    projects = ProjectModel.objects.filter(company=company).order_by('created_at')

    context = {
        "current_user" : current_user,
        "projects": projects,
        "page": "claims/create_claim.html",
    }

    if request.htmx:
        return render(request, "claims/create_claim.html", context)
    return render(request, "client/base.html", context)


# ============= SAVE PAYMENT CLAIM =============
@require_POST
def save_payment_claim(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    # Project 
    project_uuid=request.POST.get("project_uuid")
    project = ProjectModel.objects.filter(uuid=project_uuid).first()

    # Claim Info
    period_start = request.POST.get("period_start") or None
    period_end = request.POST.get("period_end") or None
    
    claim = PaymentClaimModel.objects.create(
        project=project,
        claimant_company=company,
        claim_number=request.POST.get("claim_number"),
        claim_title=request.POST.get("claim_title"),
        claim_period_start=period_start,
        claim_period_end=period_end,
        notes=request.POST.get("notes"),
        submitted_by=current_user,
    )
    

    # Claim Evidence 
    main_attachments = request.FILES.getlist("attachments")

    for attachment in main_attachments:
        if attachment.content_type.startswith("image/"):
            AttachmentsModel.objects.create(
                payment_claim_attachments=claim,
                caption=claim.claim_number,
                photo=attachment,
                project=project,
                uploaded_by_user=current_user,
            )
        else:
            AttachmentsModel.objects.create(
                payment_claim_attachments=claim,
                caption=claim.claim_number,
                file=attachment,
                project=project,
                uploaded_by_user=current_user,
            )

    # Line Items 
    line_items = []

    index = 0

    while f"line_items[{index}][description]" in request.POST:
        description = request.POST.get(
            f"line_items[{index}][description]", ""
        )

        quantity = request.POST.get(
            f"line_items[{index}][quantity]", "0"
        )

        unit = request.POST.get(
            f"line_items[{index}][unit]", "each"
        )

        custom_unit = request.POST.get(
            f"line_items[{index}][custom_unit]", ""
        )

        rate = request.POST.get(
            f"line_items[{index}][rate]", "0"
        )

        # Evidence uploaded specifically for this item
        item_attachments = request.FILES.getlist(
            f"line_items[{index}][attachments]"
        )

        line_items.append({
            "description": description,
            "quantity": quantity,
            "unit": unit,
            "custom_unit": custom_unit,
            "rate": rate,
            "attachments": item_attachments,
        })

        index += 1

    # Print each line item individually
    # for index, item in enumerate(line_items):
    #     save_claim_line = PaymentClaimLineItemModel.objects.create(
    #         payment_claim=claim,
    #         description=item['description'],
    #         quantity=item['quantity'],
    #         unit=item['unit'],
    #         custom_unit=item['custom_unit'],
    #         rate=item['rate'],
    #     ) 

    # Save each line item
    for index, item in enumerate(line_items):
        try:
            quantity = Decimal(item["quantity"])
            rate = Decimal(item["rate"])

            save_claim_line = PaymentClaimLineItemModel.objects.create(
                payment_claim=claim,
                description=item["description"],
                quantity=quantity,
                unit=item["unit"],
                custom_unit=item["custom_unit"],
                rate=rate,
            )

        except (InvalidOperation, TypeError, ValueError) as e:
            print(f"Error saving line item {index + 1}: {e}")

        # Supporting Evidence
        for attachment in item["attachments"]:
            if attachment.content_type.startswith("image/"):
                AttachmentsModel.objects.create(
                    claimLineItem_attachments=save_claim_line,
                    caption=save_claim_line.description,
                    photo=attachment,
                    project=project,
                    uploaded_by_user=current_user,
                )
            else:
                AttachmentsModel.objects.create(
                    claimLineItem_attachments=save_claim_line,
                    caption=save_claim_line.description,
                    file=attachment,
                    project=project,
                    uploaded_by_user=current_user,
                )


    context = {
        "company": company,
        "claim": claim,
    }

    response = render(
        request,
        "partials/claim_details_partial.html",
        context,
    )

    response["HX-Push-Url"] = reverse(
        "claims:claim",
        kwargs={"claim_uuid": claim.uuid},
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Claim Created",
            "message": "Claim successfully created.",
        }
    })

    return response



# ============= ALL CLAIMS VIEW =============
def PaymentClaimsView(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    claims = PaymentClaimModel.objects.filter(
    claimant_company=company
    ).select_related(
        "project",
        "claimant_company",
        "recipient_company",
    ).prefetch_related(
        "line_items",
    )

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if search_query:
        claims = claims.filter(
            Q(claim_number__icontains=search_query)
            | Q(claim_title__icontains=search_query)
            | Q(project__project_name__icontains=search_query)
        )

    valid_statuses = {
        value for value, label in PaymentClaimModel.STATUS_CHOICES
    }

    if status_filter in valid_statuses:
        claims = claims.filter(status=status_filter)

    # Aggregate the actual line-item and payment totals.
    total_claimed = sum(
        (claim.total_amount for claim in claims),
        Decimal("0.00"),
    )

    # total_paid = sum(
    #     (claim.total_paid for claim in claims),
    #     Decimal("0.00"),
    # )

    # outstanding = total_claimed - total_paid

    awaiting_action = claims.filter(
        status__in=["submitted", "under_review", "queried"]
    ).count()

    paid_claims = claims.filter(status="paid").count()

    context = {
        "current_user" : current_user,
        "claims": claims,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": PaymentClaimModel.STATUS_CHOICES,
        "total_claimed": total_claimed,
        # "total_paid": total_paid,
        # "outstanding": outstanding,
        "awaiting_action": awaiting_action,
        "paid_claims": paid_claims,
        "page": "claims/claims.html",
    }

    if request.htmx:
        return render(request, "claims/claims.html", context)
    return render(request, "client/base.html", context)


# ============= PAYMENT CLAIM DETAILS PAGE =============
def ClaimDetailsView(request,claim_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    claim = get_object_or_404(
        PaymentClaimModel.objects.filter(
            Q(claimant_company=company)
            | Q(recipient_company=company)
        ).select_related(
            "project",
            "claimant_company",
            "recipient_company",
            "submitted_by",
        ).prefetch_related(
            Prefetch(
                "line_items",
                queryset=PaymentClaimLineItemModel.objects.order_by(
                    "sort_order", "created_at"
                ).prefetch_related("claimLineItem_attachments"),
            ),
            "payment_claim_attachments",
        ),
        uuid=claim_uuid,
    )
    

    # Real claim-level supporting documents.
    claim_attachments = claim.payment_claim_attachments.all()

    # Real line items and their supporting evidence.
    line_items = claim.line_items.all()

    # Temporary demo data — replace when the Payment model exists.
    demo_payments = [
        {
            "reference": "PAY-DEMO-001",
            "date": None,
            "description": "Example progress payment",
            "amount": Decimal("0.00"),
            "status": "Example only",
        },
    ]

    # No payment model has been supplied for this implementation.
    # Do not treat demo payments as actual money received.
    total_paid = Decimal("0.00")
    outstanding_amount = claim.total_amount - total_paid

    # Temporary demo records — not persisted.
    demo_disputes = [
        {
            "title": "Example: quantity clarification",
            "description": "Confirm the measured quantity for a line item.",
            "status": "Open (demo)",
            "date": None,
        },
    ]

    demo_follow_ups = [
        {
            "title": "Example: follow up on claim review",
            "description": "Check whether the recipient has reviewed the claim.",
            "due_date": None,
            "status": "Pending (demo)",
        },
    ]

    demo_activity = [
        {
            "title": "Claim created",
            "description": "Claim record created in ClaimLedger.",
            "date": claim.created_at,
            "demo": False,
        },
    ]

    if claim.submitted_at:
        demo_activity.append({
            "title": "Claim submitted",
            "description": "Recorded submission date.",
            "date": claim.submitted_at,
            "demo": False,
        })

    demo_activity.append({
        "title": "Example review event",
        "description": "Illustrative activity; no review-history model exists yet.",
        "date": None,
        "demo": True,
    })


    context = {
        "current_user" : current_user,
        "claim": claim,
        "line_items": line_items,
        "claim_attachments": claim_attachments,
        "total_claimed": claim.total_amount,
        "total_paid": total_paid,
        "outstanding_amount": outstanding_amount,
        "demo_payments": demo_payments,
        "demo_disputes": demo_disputes,
        "demo_follow_ups": demo_follow_ups,
        "demo_activity": demo_activity,
        "page": "claims/claim_details.html",
    }

    if request.htmx:
        return render(request, "claims/claim_details.html", context)
    return render(request, "client/base.html", context)


# ============= UPDATE PROJECT =============
@require_POST
def update_claim_details_view(request,claim_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    claim = get_object_or_404(
        PaymentClaimModel.objects.filter(
            Q(claimant_company=company)
            | Q(recipient_company=company)
        ).select_related(
            "project",
            "claimant_company",
            "recipient_company",
            "submitted_by",
        ).prefetch_related(
            Prefetch(
                "line_items",
                queryset=PaymentClaimLineItemModel.objects.order_by(
                    "sort_order", "created_at"
                ).prefetch_related("claimLineItem_attachments"),
            ),
            "payment_claim_attachments",
        ),
        uuid=claim_uuid,
    )


    # START UPDATE FORM ======
    start_date = request.POST.get("claim_period_start") or None
    end_date = request.POST.get("claim_period_end") or None

    # Convert to date objects only if dates were provided
    start_date_obj = (
        datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date else None
    )

    end_date_obj = (
        datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date else None
    )

    
    claim.claim_number = request.POST.get("claim_number")
    claim.claim_title = request.POST.get("claim_title")
    claim.claim_title = request.POST.get("claim_title")
    claim.claim_period_start = start_date_obj
    claim.claim_period_end = end_date_obj 
    claim.notes = request.POST.get("notes")
    claim.save()
    # END UPDATE FORM ======


    # Real claim-level supporting documents.
    claim_attachments = claim.payment_claim_attachments.all()

    # Real line items and their supporting evidence.
    line_items = claim.line_items.all()

    # Temporary demo data — replace when the Payment model exists.
    demo_payments = [
        {
            "reference": "PAY-DEMO-001",
            "date": None,
            "description": "Example progress payment",
            "amount": Decimal("0.00"),
            "status": "Example only",
        },
    ]

    # No payment model has been supplied for this implementation.
    # Do not treat demo payments as actual money received.
    total_paid = Decimal("0.00")
    outstanding_amount = claim.total_amount - total_paid

    # Temporary demo records — not persisted.
    demo_disputes = [
        {
            "title": "Example: quantity clarification",
            "description": "Confirm the measured quantity for a line item.",
            "status": "Open (demo)",
            "date": None,
        },
    ]

    demo_follow_ups = [
        {
            "title": "Example: follow up on claim review",
            "description": "Check whether the recipient has reviewed the claim.",
            "due_date": None,
            "status": "Pending (demo)",
        },
    ]

    demo_activity = [
        {
            "title": "Claim created",
            "description": "Claim record created in ClaimLedger.",
            "date": claim.created_at,
            "demo": False,
        },
    ]

    if claim.submitted_at:
        demo_activity.append({
            "title": "Claim submitted",
            "description": "Recorded submission date.",
            "date": claim.submitted_at,
            "demo": False,
        })

    demo_activity.append({
        "title": "Example review event",
        "description": "Illustrative activity; no review-history model exists yet.",
        "date": None,
        "demo": True,
    })
    

    response = render(
        request,
        "partials/claim_details_partial.html",
        {
            "current_user" : current_user,
            "claim": claim,
            "line_items": line_items,
            "claim_attachments": claim_attachments,
            "total_claimed": claim.total_amount,
            "total_paid": total_paid,
            "outstanding_amount": outstanding_amount,
            "demo_payments": demo_payments,
            "demo_disputes": demo_disputes,
            "demo_follow_ups": demo_follow_ups,
            "demo_activity": demo_activity,
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Claim Updated",
            "message": "Claim successfully Updated."
        }
    })

    return response


# ============= DELETE PROJECT =============
@require_POST
def delete_payment_claim(request, claim_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    # DELETE CLAIM 
    claim = get_object_or_404(
        PaymentClaimModel.objects.filter(
            Q(claimant_company=company)
        ),
        uuid=claim_uuid,
    )

    claim.delete()

    claims = PaymentClaimModel.objects.filter(
    claimant_company=company
    ).select_related(
        "project",
        "claimant_company",
        "recipient_company",
    ).prefetch_related(
        "line_items",
    )

    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if search_query:
        claims = claims.filter(
            Q(claim_number__icontains=search_query)
            | Q(claim_title__icontains=search_query)
            | Q(project__project_name__icontains=search_query)
        )

    valid_statuses = {
        value for value, label in PaymentClaimModel.STATUS_CHOICES
    }

    if status_filter in valid_statuses:
        claims = claims.filter(status=status_filter)

    # Aggregate the actual line-item and payment totals.
    total_claimed = sum(
        (claim.total_amount for claim in claims),
        Decimal("0.00"),
    )

    # total_paid = sum(
    #     (claim.total_paid for claim in claims),
    #     Decimal("0.00"),
    # )

    # outstanding = total_claimed - total_paid

    awaiting_action = claims.filter(
        status__in=["submitted", "under_review", "queried"]
    ).count()

    paid_claims = claims.filter(status="paid").count()

    context = {
        "current_user" : current_user,
        "claims": claims,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": PaymentClaimModel.STATUS_CHOICES,
        "total_claimed": total_claimed,
        # "total_paid": total_paid,
        # "outstanding": outstanding,
        "awaiting_action": awaiting_action,
        "paid_claims": paid_claims,
        "page": "claims/claims.html",
    }

    response = render(
        request,
        "partials/claims_partial.html",
        context,
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Claim Deleted",
            "message": "Claim successfully deleted."
        }
    })

    return response


# ============= CLAIM LINE ITEM DETAILS VIEW =============
def ClaimLineItemDetailsView(request, item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    claim = item.payment_claim

    # Only the two companies involved in the claim can access this page.
    is_claimant = claim.claimant_company_id == company.pk
    is_recipient = claim.recipient_company_id == company.pk

    if not (is_claimant or is_recipient):
        messages.error(request, "You do not have permission to view this line item.")
        return redirect("claims:payment-claims")

    can_edit_item = is_claimant and claim.status == "draft"

    if request.method == "POST":
        action = request.POST.get("action", "")

        # EDIT LINE ITEM
        if action == "edit_item":
            if not can_edit_item:
                messages.error(
                    request,
                    "Only the claimant can edit line items while the claim is a draft.",
                )
                return redirect(
                    "claims:claim-line-item",
                    item_uuid=item.uuid,
                )

            description = request.POST.get("description", "").strip()
            unit = request.POST.get("unit", "each")
            custom_unit = request.POST.get("custom_unit", "").strip()

            try:
                quantity = Decimal(request.POST.get("quantity", ""))
                rate = Decimal(request.POST.get("rate", ""))
            except (InvalidOperation, TypeError, ValueError):
                messages.error(request, "Enter a valid quantity and rate.")
                return redirect("claims:claim-line-item", item_uuid=item.uuid)

            valid_units = dict(PaymentClaimLineItemModel.UNIT_CHOICES)

            if not description:
                messages.error(request, "Enter a description for this line item.")
            elif quantity <= 0:
                messages.error(request, "Quantity must be greater than zero.")
            elif rate < 0:
                messages.error(request, "Rate cannot be negative.")
            elif unit not in valid_units:
                messages.error(request, "Select a valid unit.")
            elif unit == "other" and not custom_unit:
                messages.error(request, "Enter the custom unit.")
            else:
                item.description = description
                item.quantity = quantity
                item.rate = rate
                item.unit = unit
                item.custom_unit = custom_unit if unit == "other" else ""
                item.save()

                messages.success(request, "Line item updated successfully.")
                return redirect("claims:claim-line-item", item_uuid=item.uuid)

        # CREATE A QUERY
        elif action == "create_query":
            reason = request.POST.get("reason", "").strip()
            description = request.POST.get("query_description", "").strip()

            if not reason or not description:
                messages.error(request, "Enter both a query reason and description.")
            elif len(reason) > 150:
                messages.error(request, "The query reason must be 150 characters or fewer.")
            else:
                ClaimQueryModel.objects.create(
                    claim_item=item,
                    reason=reason,
                    description=description,
                    created_by_user=request.user.usermodel,
                    created_by_contractor=company,
                )

                messages.success(request, "Query raised successfully.")
                return redirect("claims:claim-line-item", item_uuid=item.uuid)

        # RESPOND TO AN EXISTING QUERY
        elif action == "respond_query":
            query_uuid = request.POST.get("query_uuid")
            message = request.POST.get("message", "").strip()

            query = get_object_or_404(
                ClaimQueryModel,
                uuid=query_uuid,
                claim_item=item,
            )

            if query.status == "resolved":
                messages.error(request, "This query is resolved. Reopen it before replying.")
            elif not message:
                messages.error(request, "Enter a response before submitting.")
            else:
                ClaimQueryResponseModel.objects.create(
                    query=query,
                    message=message,
                    created_by_user=request.user.usermodel,
                    created_by_contractor=company,
                )

                if query.status == "open":
                    query.status = "responded"
                    query.save(update_fields=["status", "updated_at"])

                messages.success(request, "Response added successfully.")
                return redirect("claims:claim-line-item", item_uuid=item.uuid)

        # RESOLVE OR REOPEN A QUERY
        elif action == "update_query_status":
            query_uuid = request.POST.get("query_uuid")
            new_status = request.POST.get("new_status")

            query = get_object_or_404(
                ClaimQueryModel,
                uuid=query_uuid,
                claim_item=item,
            )

            if new_status not in ("resolved", "reopened"):
                messages.error(request, "Invalid query status.")
            elif new_status == "reopened" and query.status != "resolved":
                messages.error(request, "Only resolved queries can be reopened.")
            elif new_status == "resolved" and query.status == "resolved":
                messages.info(request, "This query is already resolved.")
            else:
                query.status = new_status
                query.save(update_fields=["status", "updated_at"])

                messages.success(request, f"Query marked as {new_status}.")
                return redirect("claims:claim-line-item", item_uuid=item.uuid)

        else:
            messages.error(request, "Unknown action.")

        return redirect("claims:claim-line-item", item_uuid=item.uuid)

    attachments = item.claimLineItem_attachments.all()
    # queries = item.queries.all()
    queries = item.queries.filter(type="query").order_by("-created_at")
    disputes = item.queries.filter(type="dispute").order_by("-created_at")

    # Certification  
    claimed_amount = item.amount or Decimal("0.00")
    certified_amount = item.certified_amount
    certification_difference = None

    if certified_amount is not None:
        certification_difference = claimed_amount - certified_amount

    context = {
        "current_user" : current_user,
        "item": item,
        "claim": claim,
        "attachments": attachments,
        "queries": queries,
        "disputes": disputes,
        "is_claimant": is_claimant,
        "is_recipient": is_recipient,
        "can_edit_item": can_edit_item,
        "open_query_count": queries.exclude(status="resolved").count(),
        # Certification
        "claimed_amount": claimed_amount,
        "certified_amount": certified_amount,
        "certification_difference": certification_difference,
        "can_certify_item": (
            is_recipient
            and claim.status in [
                "submitted",
                "under_review",
                "queried",
                "resubmitted",
            ]
        ),
        "page": "claims/claim_line_item_details.html",
    }

    if request.htmx:
        return render(request, "claims/claim_line_item_details.html", context)
    return render(request, "client/base.html", context)


# ============= UPDATE CLAIM LINE ITEM =============
@require_POST
def update_line_item(request,item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    certified_amount_input = request.POST.get(
        "certified_amount", ""
    ).strip()

    certification_notes = request.POST.get(
        "certification_notes", ""
    ).strip()

    try:
        quantity = Decimal(request.POST.get("quantity", ""))
        rate = Decimal(request.POST.get("rate", ""))

        certified_amount = (
            Decimal(certified_amount_input)
            if certified_amount_input
            else None
        )

    except (InvalidOperation, ValueError):
        # Return your form with a validation error.
        ...

    # Validate amounts
    if (
        not quantity.is_finite()
        or quantity <= 0
        or not rate.is_finite()
        or rate < 0
        or (
            certified_amount is not None
            and (
                not certified_amount.is_finite()
                or certified_amount < 0
            )
        )
    ):
        # Return your form with a validation error.
        ...

    # Update Item
    item.description = request.POST.get("description", "").strip()
    item.unit = request.POST.get("unit", "each")
    item.custom_unit = request.POST.get("custom_unit", "").strip()
    item.quantity = quantity
    item.rate = rate
    item.certified_amount = certified_amount
    item.certification_notes = certification_notes

    # Require a reason when the certified amount is lower.
    claimed_amount = (quantity * rate).quantize(Decimal("0.01"))

    if (
        certified_amount is not None
        and certified_amount < claimed_amount
        and not certification_notes
    ):
        # Return your form with a validation error.
        ...

    item.save()

    claim = item.payment_claim
    
    # Only the two companies involved in the claim can access this page.
    is_claimant = claim.claimant_company_id == company.pk
    is_recipient = claim.recipient_company_id == company.pk

    attachments = item.claimLineItem_attachments.all()
    queries = item.queries.all()

    can_edit_item = is_claimant and claim.status == "draft"

    # Certification  
    claimed_amount = item.amount or Decimal("0.00")
    certified_amount = item.certified_amount
    

    certification_difference = None

    if certified_amount is not None:
        certification_difference = claimed_amount - certified_amount

    response = render(
        request,
        "partials/claim_line_item_partial.html",
        {
            "current_user" : current_user,
            "item": item,
            "claim": claim,
            "attachments": attachments,
            "queries": queries,
            "is_claimant": is_claimant,
            "is_recipient": is_recipient,
            "can_edit_item": can_edit_item,
            "open_query_count": queries.exclude(status="resolved").count(),
            
            # Certification
            "claimed_amount": claimed_amount,
            "certified_amount": certified_amount,
            "certification_difference": certification_difference,
            "can_certify_item": (
                is_recipient
                and claim.status in [
                    "submitted",
                    "under_review",
                    "queried",
                    "resubmitted",
                ]
            ),
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Item Updated",
            "message": "Item successfully Updated."
        }
    })

    return response

# ============= ADD LINE ITEM EVIDENCE ATTACHMENT =============
@require_POST
def add_line_item_evidence(request,item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    item = get_object_or_404(PaymentClaimLineItemModel,uuid=item_uuid)

    # LINE ITEM ATTACHMENTS
    main_attachments = request.FILES.getlist("supporting_documents")
    for attachment in main_attachments:
        if attachment.content_type.startswith("image/"):
            AttachmentsModel.objects.create(
                claimLineItem_attachments=item,
                photo=attachment,
                caption=attachment.name,
                uploaded_by_user=current_user,
            )

        else:
            AttachmentsModel.objects.create(
                claimLineItem_attachments=item,
                file=attachment,
                caption=attachment.name,
                uploaded_by_user=current_user,
            )
    # LINE ITEM ATTACHMENTS END


    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
        ),
        uuid=item_uuid,
    )

    attachments = item.claimLineItem_attachments.all()

    response = render(
        request,
        "partials/line_item_evidence_partial.html",
        {
            "current_user" : current_user,
            "item": item,
            "attachments": attachments,
           
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Evidence Added",
            "message": "Evidence successfully added."
        }
    })

    return response



# ============= DELETE LINE ITEM EVIDENCE ATTACHMENT =============
@require_POST
def delete_line_item_evidence(request,item_uuid, attachment_id):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    # Delete attachment and its stored file/image
    delete_attachment = AttachmentsModel.objects.filter(
        id=attachment_id
    ).first()

    if delete_attachment:
        if delete_attachment.photo:
            delete_attachment.photo.delete(save=False)

        if delete_attachment.file:
            delete_attachment.file.delete(save=False)

        delete_attachment.delete()


    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
        ),
        uuid=item_uuid,
    )

    attachments = item.claimLineItem_attachments.all()

    response = render(
        request,
        "partials/line_item_evidence_partial.html",
        {
            "current_user" : current_user,
            "item": item,
            "attachments": attachments,
           
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Attachment Deleted",
            "message": "Attachment deleted successfully."
        }
    })

    return response

# ============= CREATE OR UPDATE CERTIFIED AMOUNT =============
@require_POST
def create_certified_line_amount(request,item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    certified_amount_input = request.POST.get(
        "certified_amount", ""
    ).strip()

    certification_notes = request.POST.get(
        "certification_notes", ""
    ).strip()

    try:
        quantity = item.quantity
        rate = item.rate

        certified_amount = (
            Decimal(certified_amount_input)
            if certified_amount_input
            else None
        )

    except (InvalidOperation, ValueError):
        # Return your form with a validation error.
        ...

    # Validate amounts
    if (
        not quantity.is_finite()
        or quantity <= 0
        or not rate.is_finite()
        or rate < 0
        or (
            certified_amount is not None
            and (
                not certified_amount.is_finite()
                or certified_amount < 0
            )
        )
    ):
        # Return your form with a validation error.
        ...

    # Update Certificate
    item.certified_amount = certified_amount
    item.certification_notes = certification_notes

    # Require a reason when the certified amount is lower.
    claimed_amount = (quantity * rate).quantize(Decimal("0.01"))

    if (
        certified_amount is not None
        and certified_amount < claimed_amount
        and not certification_notes
    ):
        # Return your form with a validation error.
        ...

    item.save()

    # CERTIFICATION ATTACHMENTS START 
    main_attachments = request.FILES.getlist("supporting_documents")

    for attachment in main_attachments:
        # print("Name:", attachment.name)
        # print("Content type:", attachment.content_type)
        # print("Size:", attachment.size)
        # print("Is image:", attachment.content_type.startswith("image/"))

        if attachment.content_type.startswith("image/"):
            saved_attachment = ClaimCertificationAttachmentModel.objects.create(
                line_item=item,
                photo=attachment,
                original_filename=attachment.name,
                uploaded_by_user=current_user,
            )
            # print("Saved photo:", saved_attachment.photo.name)

        else:
            saved_attachment = ClaimCertificationAttachmentModel.objects.create(
                line_item=item,
                file=attachment,
                original_filename=attachment.name,
                uploaded_by_user=current_user,
            )
            # print("Saved file:", saved_attachment.file.name)

    # main_attachments = request.FILES.getlist("supporting_documents")
    # for attachment in main_attachments:
    #     if attachment.content_type.startswith("image/"):
    #         ClaimCertificationAttachmentModel.objects.create(
    #             line_item=item,
    #             photo=attachment,
    #             original_filename=attachment.name,
    #             uploaded_by_user=current_user,
    #         )
    #     else:
    #         ClaimCertificationAttachmentModel.objects.create(
    #             line_item=item,
    #             file=attachment,
    #             original_filename=attachment.name,
    #             uploaded_by_user=current_user,
    #         )
    # CERTIFICATION ATTACHMENTS END 

    claim = item.payment_claim
    
    # Only the two companies involved in the claim can access this page.
    is_claimant = claim.claimant_company_id == company.pk
    is_recipient = claim.recipient_company_id == company.pk

    attachments = item.claimLineItem_attachments.all()
    queries = item.queries.all()

    can_edit_item = is_claimant and claim.status == "draft"

    # Certification  
    claimed_amount = item.amount or Decimal("0.00")
    certified_amount = item.certified_amount
    

    certification_difference = None

    if certified_amount is not None:
        certification_difference = claimed_amount - certified_amount

    response = render(
        request,
        "partials/claim_line_item_partial.html",
        {
            "current_user" : current_user,
            "item": item,
            "claim": claim,
            "attachments": attachments,
            "queries": queries,
            "is_claimant": is_claimant,
            "is_recipient": is_recipient,
            "can_edit_item": can_edit_item,
            "open_query_count": queries.exclude(status="resolved").count(),
            
            # Certification
            "claimed_amount": claimed_amount,
            "certified_amount": certified_amount,
            "certification_difference": certification_difference,
            "can_certify_item": (
                is_recipient
                and claim.status in [
                    "submitted",
                    "under_review",
                    "queried",
                    "resubmitted",
                ]
            ),
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Certification Updated",
            "message": "Certification successfully Updated."
        }
    })

    return response


# ============= DELETE CERTIFICATED ATTACHMENT =============
@require_POST
def delete_certified_line_attachment(request,item_uuid, attachment_id):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    # Delete attachment and its stored file/image
    delete_attachment = ClaimCertificationAttachmentModel.objects.filter(
        id=attachment_id
    ).first()

    if delete_attachment:
        if delete_attachment.photo:
            delete_attachment.photo.delete(save=False)

        if delete_attachment.file:
            delete_attachment.file.delete(save=False)

        delete_attachment.delete()

    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    claim = item.payment_claim

    # Only the two companies involved in the claim can access this page.
    is_claimant = claim.claimant_company_id == company.pk
    is_recipient = claim.recipient_company_id == company.pk

    can_edit_item = is_claimant and claim.status == "draft"

    attachments = item.claimLineItem_attachments.all()
    queries = item.queries.all()

    # Certification  
    claimed_amount = item.amount or Decimal("0.00")
    certified_amount = item.certified_amount
    certification_difference = None

    if certified_amount is not None:
        certification_difference = claimed_amount - certified_amount


    response = render(
        request,
        "partials/claim_line_item_partial.html",
        {
            "current_user" : current_user,
            "item": item,
            "claim": claim,
            "attachments": attachments,
            "queries": queries,
            "is_claimant": is_claimant,
            "is_recipient": is_recipient,
            "can_edit_item": can_edit_item,
            "open_query_count": queries.exclude(status="resolved").count(),
            
            # Certification
            "claimed_amount": claimed_amount,
            "certified_amount": certified_amount,
            "certification_difference": certification_difference,
            "can_certify_item": (
                is_recipient
                and claim.status in [
                    "submitted",
                    "under_review",
                    "queried",
                    "resubmitted",
                ]
            ),
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Attachment Deleted",
            "message": "Attachment deleted successfully."
        }
    })

    return response


# ============= CRATE LINE ITEM QUERY =============
@require_POST
def create_line_item_query(request,item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    form_action = request.POST.get("form_action", "")

    # CREATE QUERY FUNCTION START 
    if form_action == 'create_new_query':
        reason = request.POST.get("reason", "").strip()
        description = request.POST.get("query_description", "").strip()
        query = ClaimQueryModel.objects.create(
            claim_item=item,
            reason=reason,
            description=description,
            created_by_user=current_user,
        )
            

        # CREATE QUERY FUNCTION END 

        # QUERY ATTACHMENTS START 
        main_attachments = request.FILES.getlist("supporting_documents")
        for attachment in main_attachments:
            if attachment.content_type.startswith("image/"):
                QueriesResponsesAttachmentModel.objects.create(
                    query=query,
                    photo=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )

            else:
                QueriesResponsesAttachmentModel.objects.create(
                    query=query,
                    file=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )
        # QUERY ATTACHMENTS END 

    elif form_action == 'create_response':
        # CREATE RESPONSE FUNCTION START 
        query_uuid = request.POST.get("query_uuid")
        query = get_object_or_404(
            ClaimQueryModel,
            uuid=query_uuid,
            claim_item=item,
        )

        message = request.POST.get("message", "").strip()
        create_response = ClaimQueryResponseModel.objects.create(
            query=query,
            message=message,
            created_by_user=current_user,
        )

        # RESPONSE ATTACHMENTS START 
        main_attachments = request.FILES.getlist("supporting_documents")
        for attachment in main_attachments:
            if attachment.content_type.startswith("image/"):
                QueriesResponsesAttachmentModel.objects.create(
                    response=create_response,
                    photo=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )

            else:
                QueriesResponsesAttachmentModel.objects.create(
                    response=create_response,
                    file=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )
        # RESPONSE ATTACHMENTS END

        if query.status == "open":
            query.status = "responded"
            query.save(update_fields=["status", "updated_at"])


    elif form_action == 'update_query_status':
        query_uuid = request.POST.get("query_uuid")
        new_status = request.POST.get("new_status")

        query = get_object_or_404(
            ClaimQueryModel,
            uuid=query_uuid,
            claim_item=item,
        )

        query.status = new_status
        query.save(update_fields=["status", "updated_at"])
    elif form_action == 'delete_query':
        query_uuid = request.POST.get("query_uuid")
        query = get_object_or_404(ClaimQueryModel,uuid=query_uuid,claim_item=item,)
        query.delete()

    elif form_action == 'delete_response':
        response_uuid = request.POST.get("response_uuid")
        response_delete = get_object_or_404(ClaimQueryResponseModel,uuid=response_uuid)
        response_delete.delete()


    # GET ALL QUERIES 
    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )

    
    queries = item.queries.all()

    response = render(
        request,
        "partials/line_item_queries_partial.html",
        {
            "item" : item,
            "queries": queries,
            "open_query_count": queries.exclude(status="resolved").count(),
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Query Created",
            "message": "Query raised successfully."
        }
    })

    return response


# ============= LINE ITEM DISPUTES VIEW =============
@require_POST
def line_item_dispute_view(request,item_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    item = get_object_or_404(PaymentClaimLineItemModel,uuid=item_uuid)

    form_action = request.POST.get("form_action", "")

    # CREATE NEW DISPUTE 
    if form_action == 'create_new_dispute':
        reason = request.POST.get("reason", "").strip()
        dispute_amount = request.POST.get("dispute_amount", "").strip()
        description = request.POST.get("dispute_description", "").strip()

        dispute = ClaimQueryModel.objects.create(
            claim_item=item,
            reason=reason,
            dispute_amount=dispute_amount,
            description=description,
             type="dispute",
            created_by_user=current_user,
        )

        # Supporting Documents 
        main_attachments = request.FILES.getlist("supporting_documents")
        for attachment in main_attachments:
            if attachment.content_type.startswith("image/"):
                QueriesResponsesAttachmentModel.objects.create(
                    query=dispute,
                    photo=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )

            else:
                QueriesResponsesAttachmentModel.objects.create(
                    query=dispute,
                    file=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )

        # Dispute Created
        alert_title = "Dispute Raised"
        alert_message = "Your dispute has been raised successfully."

    # UPDATE DISPUTE STATUS 
    elif form_action == 'update_dispute_status':
        dispute_uuid = request.POST.get("dispute_uuid")
        new_status = request.POST.get("new_status")

        dispute = get_object_or_404(
            ClaimQueryModel,
            uuid=dispute_uuid,
            claim_item=item,
        )

        dispute.status = new_status
        dispute.save(update_fields=["status", "updated_at"])

        # Alert Values 
        # Dispute Updated
        alert_title = "Dispute Status Updated"
        alert_message = "The dispute status has been updated successfully."

    # DELETE DISPUTE 
    elif form_action == 'delete_dispute':
        dispute_uuid = request.POST.get("dispute_uuid")
        dispute = get_object_or_404(ClaimQueryModel,uuid=dispute_uuid,claim_item=item,)
        dispute.delete()

        # Dispute Deleted
        alert_title = "Dispute Deleted"
        alert_message = "The dispute has been deleted successfully."

    # CREATE RESPONSE 
    elif form_action == 'create_response':
        dispute_uuid = request.POST.get("dispute_uuid")
        dispute = get_object_or_404(
            ClaimQueryModel,
            uuid=dispute_uuid,
            claim_item=item,
        )

        message = request.POST.get("message", "").strip()
        create_response = ClaimQueryResponseModel.objects.create(
            query=dispute,
            message=message,
            created_by_user=current_user,
        )

        main_attachments = request.FILES.getlist("supporting_documents")
        for attachment in main_attachments:
            if attachment.content_type.startswith("image/"):
                QueriesResponsesAttachmentModel.objects.create(
                    response=create_response,
                    photo=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )

            else:
                QueriesResponsesAttachmentModel.objects.create(
                    response=create_response,
                    file=attachment,
                    original_filename=attachment.name,
                    uploaded_by_user=current_user,
                )
        # Update Dispute Status 
        if dispute.status == "open":
            dispute.status = "responded"
            dispute.save(update_fields=["status", "updated_at"])

        # Response Created
        alert_title = "Response Added"
        alert_message = "Your response has been submitted successfully."

    # DELETE RESPONSE 
    elif form_action == 'delete_response':
        response_uuid = request.POST.get("response_uuid")
        response_delete = get_object_or_404(ClaimQueryResponseModel,uuid=response_uuid)

        # Update Dispute Status 
        dispute = response_delete.query
        if dispute.status == "responded":
            dispute.status = "open"
            dispute.save(update_fields=["status", "updated_at"])

        response_delete.delete()

        # Response Deleted
        alert_title = "Response Deleted"
        alert_message = "The response has been deleted successfully."


    # GET LATEST DATA 
    item = get_object_or_404(
        PaymentClaimLineItemModel.objects.select_related(
            "payment_claim",
            "payment_claim__project",
            "payment_claim__claimant_company",
            "payment_claim__recipient_company",
        ).prefetch_related(
            Prefetch(
                "claimLineItem_attachments",
                queryset=AttachmentsModel.objects.select_related(
                    "uploaded_by_user",
                    "uploaded_by_contractor",
                ),
            ),
            Prefetch(
                "queries",
                queryset=ClaimQueryModel.objects.select_related(
                    "created_by_user",
                    "created_by_contractor",
                ).prefetch_related(
                    Prefetch(
                        "responses",
                        queryset=ClaimQueryResponseModel.objects.select_related(
                            "created_by_user",
                            "created_by_contractor",
                        ),
                    )
                ),
            ),
        ),
        uuid=item_uuid,
    )
    
    disputes = item.queries.filter(type="dispute").order_by("-created_at")

    response = render(
        request,
        "partials/line_item_dispute_partial.html",
        {
            "item" : item,
            "disputes": disputes,
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": alert_title,
            "message": alert_message
        }
    })

    return response

# ============= CLAIM DETAILS CHATGPT =============
def ClaimDetailsViewChatGpt(request, claim_uuid):
    # Adapt this to the company relationship in your UserModel.
    company = request.user.usermodel.company

    claim = get_object_or_404(
        PaymentClaimModel.objects.filter(
            Q(claimant_company=company)
            | Q(recipient_company=company)
        ).select_related(
            "project",
            "claimant_company",
            "recipient_company",
            "submitted_by",
        ).prefetch_related(
            Prefetch(
                "line_items",
                queryset=PaymentClaimLineItemModel.objects.order_by(
                    "sort_order", "created_at"
                ).prefetch_related("claimLineItem_attachments"),
            ),
            "payment_claim_attachments",
        ),
        uuid=claim_uuid,
    )

    # Real claim-level supporting documents.
    claim_attachments = claim.payment_claim_attachments.all()

    # Real line items and their supporting evidence.
    line_items = claim.line_items.all()

    # Temporary demo data — replace when the Payment model exists.
    demo_payments = [
        {
            "reference": "PAY-DEMO-001",
            "date": None,
            "description": "Example progress payment",
            "amount": Decimal("0.00"),
            "status": "Example only",
        },
    ]

    # No payment model has been supplied for this implementation.
    # Do not treat demo payments as actual money received.
    total_paid = Decimal("0.00")
    outstanding_amount = claim.total_amount - total_paid

    # Temporary demo records — not persisted.
    demo_disputes = [
        {
            "title": "Example: quantity clarification",
            "description": "Confirm the measured quantity for a line item.",
            "status": "Open (demo)",
            "date": None,
        },
    ]

    demo_follow_ups = [
        {
            "title": "Example: follow up on claim review",
            "description": "Check whether the recipient has reviewed the claim.",
            "due_date": None,
            "status": "Pending (demo)",
        },
    ]

    demo_activity = [
        {
            "title": "Claim created",
            "description": "Claim record created in ClaimLedger.",
            "date": claim.created_at,
            "demo": False,
        },
    ]

    if claim.submitted_at:
        demo_activity.append({
            "title": "Claim submitted",
            "description": "Recorded submission date.",
            "date": claim.submitted_at,
            "demo": False,
        })

    demo_activity.append({
        "title": "Example review event",
        "description": "Illustrative activity; no review-history model exists yet.",
        "date": None,
        "demo": True,
    })

    context = {
        "claim": claim,
        "line_items": line_items,
        "claim_attachments": claim_attachments,
        "total_claimed": claim.total_amount,
        "total_paid": total_paid,
        "outstanding_amount": outstanding_amount,
        "demo_payments": demo_payments,
        "demo_disputes": demo_disputes,
        "demo_follow_ups": demo_follow_ups,
        "demo_activity": demo_activity,
    }

    return render(
        request,
        "claims/claim_details.html",
        context,
    )


