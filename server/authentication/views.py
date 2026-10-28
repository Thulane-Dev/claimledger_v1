from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import now
from datetime import date
from django.db.models import Q
from django.urls import reverse

from .models import *

# Extended Models
from client.models import *

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
# email imports start
from django.core.mail import send_mail
from django.conf import settings
# email imports end

# Authentication Imports start
from .forms import CreateUserForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .decorators import unauthenticated_user, allowed_user
from django.contrib.auth.models import Group
# Authentication Imports end


# Invite user password
from django.contrib.auth.forms import SetPasswordForm

# Create your views here.



@unauthenticated_user
def LoginPage(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Find the user by email, ignoring letter casing.
        matching_users = User.objects.filter(email__iexact=email)

        user = None

        # Only authenticate if exactly one account matches.
        if matching_users.count() == 1:
            user_record = matching_users.first()

            user = authenticate(
                request,
                username=user_record.username,
                password=password,
            )

        if user is not None:
            login(request, user)

            current_user = UserModel.objects.get(user=user)

            if not current_user.account_complete:
                return redirect('account:account-setup')

            return redirect('dashboard:dashboard')

        else:
            messages.error(
                request,
                'Email address or password is incorrect.'
            )

    return render(request, "authentication/login.html")



@unauthenticated_user
def RegisterUser(request):
    form = CreateUserForm()

    if request.method == 'POST' and 'create-account' in request.POST:
        form = CreateUserForm(request.POST)

        if form.is_valid():
            user = form.save()

            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            user_email = form.cleaned_data['email']

            UserModel.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=user_email,
                agreeTerms=True,
            )

            messages.success(
                request,
                f"Account successfully created for {first_name} {last_name}."
            )

            return redirect("login")

    context = {
        'form': form,
    }

    return render(
        request,
        "authentication/register.html",
        context
    )


@unauthenticated_user
def RegisterUser01(request):
    form = CreateUserForm()
    if request.method == 'POST' and 'create-account' in request.POST:
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            user_email = form.cleaned_data.get('email')

            UserModel.objects.create(
                user=user,
                first_name=username,
                email=user_email,
                agreeTerms=True,
            )

            messages.success(request, 'Account was created for ' + username)
            return redirect("login")

    context = {
        'form': form
    }
    return render(request, "authentication/register.html", context)


# logout user
def LogoutUser(request):
    logout(request)
    return redirect('login')



