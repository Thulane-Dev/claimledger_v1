from django.shortcuts import render, get_object_or_404, redirect
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q

# Models Import
from authentication.models import UserModel
from account.models import *
from projects.models import *

# ============= DASHBOARD VIEW =============
def DashboardView(request):
    user = request.user
    current_user = get_object_or_404(UserModel, user=user)
    company = current_user.company
    projects = ProjectModel.objects.filter(company=company).order_by('created_at')
    project_count = projects.count()
    add_project_target_value = 'dashboardContentTarget'

    context = {
        "projects": projects,
        "project_count": project_count,
        "add_project_target_value": add_project_target_value,
        "page": "dashboard/dashboard.html",
    }

    if request.htmx:
        return render(request, "dashboard/dashboard.html", context)
    return render(request, "client/base.html", context)
