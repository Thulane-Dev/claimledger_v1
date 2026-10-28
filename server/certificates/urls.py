
from django.urls import path
from .import views

app_name = "certificates"

urlpatterns = [
    path('certificates/',views.CertificatesView, name='certificates'),
    path('create-certificate/<uuid:claim_uuid>/',views.CreateCertificateView, name='create-certificate'),
]
