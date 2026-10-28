from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib import messages

# htmx
from django.http import HttpResponse
import json

# Models Import
from .models import *
from authentication.models import *

# ============= ACCOUNT SETUP VIEW =============
def AccountSetupView(request):
    

    return render(request, 'account/account_setup.html')


# ============= Save Account Setup =============
@require_POST
def save_account_setup(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)

    # Create Address Model Object
    save_address = AddressModel.objects.create(
        street=request.POST.get("street"),
        suburb=request.POST.get("suburb"),
        city=request.POST.get("city"),
        province=request.POST.get("province"),
        postal_code=request.POST.get("postal_code"),
        country=request.POST.get("country"),
    )

    # Create Company Profile Model Object
    save_company = CompanyModel.objects.create(
        name=request.POST.get("name"),
        registration_number=request.POST.get("registration_number"),
        vat_number=request.POST.get("vat_number"),
        email=request.POST.get("email"),
        phone=request.POST.get("phone"),
        address=save_address,
        owner=current_user,
    )

    # Update User Account Details
    current_user.company = save_company
    current_user.account_complete = True
    current_user.save()

    messages.success(
        request,
        f"🎉 Your account is all set up!"
    )

    # 🎯 Redirect To Dashboard
    url = reverse('dashboard:dashboard')
    return redirect(f"{url}")


# ============= PROFILE ACCOUNT VIEW =============
def AccountView(request):
    user = request.user
    profile = get_object_or_404(UserModel, user=user)

    context = {
        "profile" : profile,
        "page": "account/account.html",
    }

    if request.htmx:
        return render(request, "account/account.html", context)
    return render(request, "client/base.html", context)


# ============= EDIT PROFILE ACCOUNT =============
@require_POST
def update_profile(request):
    user = request.user
    profile = get_object_or_404(UserModel, user=user)

    # Update Profile 
    profile.first_name=request.POST.get("first_name")
    profile.last_name=request.POST.get("last_name")
    profile.phone=request.POST.get("phone")
    profile.save()

    response = render(
        request,
        "partials/account_partial.html",
        {
            "profile": profile,

        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Profile Updated",
            "message": "Profile successfully Updated."
        }
    })

    return response


# ============= COMPANY DETAILS VIEW =============
def CompanyDetailsView(request,company_uuid):
    user = request.user
    profile = get_object_or_404(UserModel, user=user)
    company = profile.company

    context = {
        "company" : company,
        "profile": profile,
        "province_choices": AddressModel.PROVINCE_CHOICES,
        "page": "company/company_details.html",
    }

    if request.htmx:
        return render(request, "company/company_details.html", context)
    return render(request, "client/base.html", context)


# ============= UPDATE COMPANY DETAILS =============
@require_POST
def update_company_details(request,company_uuid):
    user = request.user
    profile = get_object_or_404(UserModel, user=user)
    company = profile.company
    address = company.address

    # Update Company Info 
    company.name=request.POST.get("name")
    company.registration_number=request.POST.get("registration_number")
    company.vat_number=request.POST.get("vat_number")
    company.email=request.POST.get("email")
    company.phone=request.POST.get("phone")
    company.save()

    address.street=request.POST.get("street")
    address.suburb=request.POST.get("suburb")
    address.city=request.POST.get("city")
    address.province=request.POST.get("province")
    address.postal_code=request.POST.get("postal_code")
    address.country=request.POST.get("country")
    address.save()

    response = render(
        request,
        "partials/company_details_partial.html",
        {
            "company" : company,
            "profile": profile,
            "province_choices": AddressModel.PROVINCE_CHOICES,

        },
    )

    response["HX-Trigger"] = json.dumps({
        "claimledgerToast": {
            "type": "success",
                "title": "Company Updated",
            "message": "Company successfully Updated."
        }
    })

    return response