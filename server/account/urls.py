
from django.urls import path
from .import views

app_name = "account"

urlpatterns = [
    # Account Setup 
    path('account-setup/',views.AccountSetupView, name='account-setup'),
    path('save-account-setup', views.save_account_setup, name='save-account-setup'),

    # Account Urls 
    path('account/',views.AccountView, name='account'),
    path('update-profile/',views.update_profile, name='update-profile'),

    # Company Details 
    path('company/<uuid:company_uuid>/',views.CompanyDetailsView, name='company'),
    path('update-company-info/<uuid:company_uuid>/',views.update_company_details, name='update-company-info'),
    
]
