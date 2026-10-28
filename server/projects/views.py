from django.shortcuts import render, get_object_or_404, redirect
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q


from datetime import date,datetime
from decimal import Decimal


# htmx
from django.http import HttpResponse
import json


# Models Import
from .models import *
from authentication.models import *
from account.models import AddressModel





# ============= SAVE PROJECT =============
@require_POST
def create_project(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    # =============== Save Location ===============
    project_location = AddressModel.objects.create(
        street=request.POST.get("street"),
        suburb=request.POST.get("suburb"),
        city=request.POST.get("city"),
        postal_code=request.POST.get("postal_code"),
        province=request.POST.get("province"),
        country=request.POST.get("country"),
    )

    # =============== Save Project Object ===============
    start_date = request.POST.get("start_date") or None
    end_date = request.POST.get("end_date") or None

    ProjectModel.objects.create(
        company=company,
        created_by=current_user,
        project_name=request.POST.get("project_name"),
        site_reference=request.POST.get("site_reference"),

        client_contact_name=request.POST.get("client_contact_name"),
        client_contact_phone=request.POST.get("client_contact_phone"),
        client_contact_email=request.POST.get("client_contact_email"),

        start_date=start_date,
        end_date=end_date,

        location=project_location,
    )

    

    # Partial Target Value 
    project_target_value=request.POST.get("project_target_value")

    if project_target_value == 'dashboardContentTarget':
        # Dashboard Partial 
        projects = ProjectModel.objects.filter(company=company).order_by('created_at')
        project_count = projects.count()
        
        response = render(
            request,
            "partials/dashboard_partial.html",
            {
                "projects": projects,
                "project_count": project_count,
                "project_target_value" : project_target_value,
            },
        )
    else:
        # Company Projects Partial

        # Only retrieve projects belonging to this company.
        company_projects = ProjectModel.objects.filter(
            company=company
        ).select_related("location", "company").order_by('-created_at')
    
        # Summary counts reflect all company projects, not the filters.
        project_count = company_projects.count()
        active_count = company_projects.filter(status="active").count()
        on_hold_count = company_projects.filter(status="on_hold").count()
        completed_count = company_projects.filter(status="completed").count()
        projects = company_projects.order_by('-created_at')

        response = render(
            request,
            "partials/projects_partial.html",
            {
                "projects": projects,
                "project_count": project_count,
                "active_count": active_count,
                "on_hold_count": on_hold_count,
                "completed_count": completed_count,
                "filtered_count": projects.count(),
                "project_target_value" : project_target_value,
            },
        )


    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Project Created",
            "message": "Project successfully created."
        }
    })


    return response


# ============= COMPANY PROJECTS =============
def ProjectsView(request):
    # Adjust this relationship to match your UserModel.
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    add_project_target_value = 'projectsContentTarget'

    # Only retrieve projects belonging to this company.
    company_projects = ProjectModel.objects.filter(
        company=company
    ).select_related("location", "company").order_by('-created_at')

    # Summary counts reflect all company projects, not the filters.
    project_count = company_projects.count()
    active_count = company_projects.filter(status="active").count()
    on_hold_count = company_projects.filter(status="on_hold").count()
    completed_count = company_projects.filter(status="completed").count()

    # Search and status filtering.
    search_query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()

    projects = company_projects.order_by('-created_at')

    if search_query:
        projects = projects.filter(
            Q(project_name__icontains=search_query)
            | Q(site_reference__icontains=search_query)
            | Q(client_contact_name__icontains=search_query)
            | Q(client_contact_email__icontains=search_query)
        )

    valid_statuses = {
        choice[0] for choice in ProjectModel.STATUS_CHOICES
    }

    if selected_status in valid_statuses:
        projects = projects.filter(status=selected_status)
    else:
        selected_status = ""

    projects = projects.order_by("-created_at")

    context = {
        "projects": projects,
        "project_count": project_count,
        "active_count": active_count,
        "on_hold_count": on_hold_count,
        "completed_count": completed_count,
        "filtered_count": projects.count(),
        "search_query": search_query,
        "selected_status": selected_status,
        "add_project_target_value": add_project_target_value,
        "page": "projects/projects.html",
    }

    if request.htmx:
        return render(request, "projects/projects.html", context)
    return render(request, "client/base.html", context)



# ============= PROJECT DETAILS =============
def ProjectDetailsVieW(request,project_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    # Security: only allow access to this company's projects.
    project = get_object_or_404(
        ProjectModel.objects.select_related(
            "company",
            "location",
        ),
        uuid=project_uuid,
        company=company,
    )


    # DUMMY DATA ONLY — not stored in the database.
    dummy_claims = [
        {
            "reference": "CLM-001",
            "description": "Excavation and site preparation",
            "submitted": date(2026, 9, 12),
            "amount": "R 85,000.00",
            "amount_value": Decimal("85000.00"),
            "status": "Paid",
            "status_key": "paid",
        },
        {
            "reference": "CLM-002",
            "description": "Concrete foundation works",
            "submitted": date(2026, 10, 2),
            "amount": "R 142,500.00",
            "amount_value": Decimal("142500.00"),
            "status": "Submitted",
            "status_key": "submitted",
        },
        {
            "reference": "CLM-003",
            "description": "Structural materials and installation",
            "submitted": date(2026, 10, 16),
            "amount": "R 96,750.00",
            "amount_value": Decimal("96750.00"),
            "status": "Partially paid",
            "status_key": "partially_paid",
        },
    ]

    dummy_payments = [
        {
            "reference": "PAY-001",
            "claim_reference": "CLM-001",
            "date": date(2026, 9, 25),
            "amount": "R 85,000.00",
            "amount_value": Decimal("85000.00"),
            "method": "Bank transfer",
        },
        {
            "reference": "PAY-002",
            "claim_reference": "CLM-003",
            "date": date(2026, 10, 20),
            "amount": "R 40,000.00",
            "amount_value": Decimal("40000.00"),
            "method": "Bank transfer",
        },
    ]

    dummy_activity = [
        {
            "kind": "payment",
            "icon": "bi-check-circle",
            "title": "Payment recorded",
            "description": "R 40,000.00 recorded against CLM-003.",
            "date": date(2026, 10, 20),
        },
        {
            "kind": "claim",
            "icon": "bi-file-earmark-text",
            "title": "Claim submitted",
            "description": "CLM-003 was submitted for R 96,750.00.",
            "date": date(2026, 10, 16),
        },
        {
            "kind": "claim",
            "icon": "bi-file-earmark-text",
            "title": "Claim submitted",
            "description": "CLM-002 was submitted for R 142,500.00.",
            "date": date(2026, 10, 2),
        },
        {
            "kind": "payment",
            "icon": "bi-check-circle",
            "title": "Claim paid",
            "description": "CLM-001 was paid in full.",
            "date": date(2026, 9, 25),
        },
        {
            "kind": "project",
            "icon": "bi-building",
            "title": "Project created",
            "description": "The project was added to ClaimLedger.",
            "date": project.created_at.date(),
        },
    ]

    total_claimed_value = sum(
        claim["amount_value"] for claim in dummy_claims
    )

    paid_to_date_value = sum(
        payment["amount_value"] for payment in dummy_payments
    )

    awaiting_payment_value = total_claimed_value - paid_to_date_value

    def format_rand(value):
        return f"R {value:,.2f}"

    context = {
        "project": project,
        "dummy_claims": dummy_claims,
        "dummy_payments": dummy_payments,
        "dummy_activity": dummy_activity,
        "dummy_claim_count": len(dummy_claims),
        "dummy_total_claimed": format_rand(total_claimed_value),
        "dummy_awaiting_payment": format_rand(awaiting_payment_value),
        "dummy_paid_to_date": format_rand(paid_to_date_value),
        "page": "projects/project_details.html",
    }

    if request.htmx:
        return render(request, "projects/project_details.html", context)
    return render(request, "client/base.html", context)


# ============= UPDATE PROJECT =============
@require_POST
def update_project_view(request,project_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    # Security: only allow access to this company's projects.
    project = get_object_or_404(
        ProjectModel.objects.select_related(
            "company",
            "location",
        ),
        uuid=project_uuid,
        company=company,
    )

    start_date = request.POST.get("start_date") or None
    end_date = request.POST.get("end_date") or None

    # Convert to date objects only if dates were provided
    start_date_obj = (
        datetime.strptime(start_date, "%Y-%m-%d").date()
        if start_date else None
    )

    end_date_obj = (
        datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date else None
    )

    # Update Project Details 
    project.project_name=request.POST.get("project_name")
    project.site_reference=request.POST.get("site_reference")
    project.client_contact_name=request.POST.get("client_contact_name")
    project.client_contact_phone=request.POST.get("client_contact_phone")
    project.client_contact_email=request.POST.get("client_contact_email")
    project.start_date=start_date_obj
    project.end_date=end_date_obj
    project.save()

    # Update Project Location 
    location = project.location
    location.street=request.POST.get("street")
    location.suburb=request.POST.get("suburb")
    location.city=request.POST.get("city")
    location.postal_code=request.POST.get("postal_code")
    location.province=request.POST.get("province")
    location.country=request.POST.get("country")
    location.save()

    # DUMMY DATA ONLY — not stored in the database.
    dummy_claims = [
        {
            "reference": "CLM-001",
            "description": "Excavation and site preparation",
            "submitted": date(2026, 9, 12),
            "amount": "R 85,000.00",
            "amount_value": Decimal("85000.00"),
            "status": "Paid",
            "status_key": "paid",
        },
        {
            "reference": "CLM-002",
            "description": "Concrete foundation works",
            "submitted": date(2026, 10, 2),
            "amount": "R 142,500.00",
            "amount_value": Decimal("142500.00"),
            "status": "Submitted",
            "status_key": "submitted",
        },
        {
            "reference": "CLM-003",
            "description": "Structural materials and installation",
            "submitted": date(2026, 10, 16),
            "amount": "R 96,750.00",
            "amount_value": Decimal("96750.00"),
            "status": "Partially paid",
            "status_key": "partially_paid",
        },
    ]

    dummy_payments = [
        {
            "reference": "PAY-001",
            "claim_reference": "CLM-001",
            "date": date(2026, 9, 25),
            "amount": "R 85,000.00",
            "amount_value": Decimal("85000.00"),
            "method": "Bank transfer",
        },
        {
            "reference": "PAY-002",
            "claim_reference": "CLM-003",
            "date": date(2026, 10, 20),
            "amount": "R 40,000.00",
            "amount_value": Decimal("40000.00"),
            "method": "Bank transfer",
        },
    ]

    dummy_activity = [
        {
            "kind": "payment",
            "icon": "bi-check-circle",
            "title": "Payment recorded",
            "description": "R 40,000.00 recorded against CLM-003.",
            "date": date(2026, 10, 20),
        },
        {
            "kind": "claim",
            "icon": "bi-file-earmark-text",
            "title": "Claim submitted",
            "description": "CLM-003 was submitted for R 96,750.00.",
            "date": date(2026, 10, 16),
        },
        {
            "kind": "claim",
            "icon": "bi-file-earmark-text",
            "title": "Claim submitted",
            "description": "CLM-002 was submitted for R 142,500.00.",
            "date": date(2026, 10, 2),
        },
        {
            "kind": "payment",
            "icon": "bi-check-circle",
            "title": "Claim paid",
            "description": "CLM-001 was paid in full.",
            "date": date(2026, 9, 25),
        },
        {
            "kind": "project",
            "icon": "bi-building",
            "title": "Project created",
            "description": "The project was added to ClaimLedger.",
            "date": project.created_at.date(),
        },
    ]

    total_claimed_value = sum(
        claim["amount_value"] for claim in dummy_claims
    )

    paid_to_date_value = sum(
        payment["amount_value"] for payment in dummy_payments
    )

    awaiting_payment_value = total_claimed_value - paid_to_date_value

    def format_rand(value):
        return f"R {value:,.2f}"


    response = render(
        request,
        "partials/project_details_partial.html",
        {
            "project": project,
            "dummy_claims": dummy_claims,
            "dummy_payments": dummy_payments,
            "dummy_activity": dummy_activity,
            "dummy_claim_count": len(dummy_claims),
            "dummy_total_claimed": format_rand(total_claimed_value),
            "dummy_awaiting_payment": format_rand(awaiting_payment_value),
            "dummy_paid_to_date": format_rand(paid_to_date_value),
        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
             "title": "Project Updated",
            "message": "Project successfully Updated."
        }
    })

    return response


# ============= DELETE PROJECT =============
@require_POST
def delete_project(request, project_uuid):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company

    project = get_object_or_404(
        ProjectModel.objects.select_related(
            "company",
            "location",
        ),
        uuid=project_uuid,
        company=company,
    )

    project.location.delete()
    project.delete()

    # Only retrieve projects belonging to this company.
    company_projects = ProjectModel.objects.filter(
        company=company
    ).select_related("location", "company")

    # Summary counts reflect all company projects, not the filters.
    project_count = company_projects.count()
    active_count = company_projects.filter(status="active").count()
    on_hold_count = company_projects.filter(status="on_hold").count()
    completed_count = company_projects.filter(status="completed").count()
    projects = company_projects

    context = {
        "projects": projects,
        "project_count": project_count,
        "active_count": active_count,
        "on_hold_count": on_hold_count,
        "completed_count": completed_count,
        "filtered_count": projects.count(),
    }

    # if request.headers.get("HX-Request"):
    #     return render(
    #         request,
    #         "partials/projects_partial.html",
    #         context,
    #     )

    # return redirect("company_projects")


    # After deleting the project and querying the updated projects list
    response = render(
        request,
        "partials/projects_partial.html",
        context,
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
            "title": "Project Deleted",
            "message": "Project successfully deleted."
        }
    })

    return response




# ============= TOASTS RESPONSE TYPES =============

# response["HX-Trigger"] = json.dumps({
#     "claimledgerToast": {
#         "type": "success",
#         "title": "Project Created",
#         "message": "Project successfully created."
#     }
# })

# response["HX-Trigger"] = json.dumps({
#     "claimledgerToast": {
#         "type": "error",
#         "title": "Unable to Create Project",
#         "message": "Something went wrong. Please try again."
#     }
# })

# response["HX-Trigger"] = json.dumps({
#     "claimledgerToast": {
#         "type": "warning",
#         "title": "Missing Information",
#         "message": "Please complete the required project fields."
#     }
# })


# response["HX-Trigger"] = json.dumps({
#     "claimledgerToast": {
#         "type": "info",
#         "title": "Project Updated",
#         "message": "Your project information has been updated."
#     }
# })