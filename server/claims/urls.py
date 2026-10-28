
from django.urls import path
from .import views

app_name = "claims"

urlpatterns = [
    path('payment-claims/',views.PaymentClaimsView, name='payment-claims'),
    path('create-claim/',views.CreatePaymentClaimView, name='create-claim'),
    path('save-payment-claim/',views.save_payment_claim, name='save-payment-claim'),
    path('claim/<uuid:claim_uuid>/',views.ClaimDetailsView, name='claim'),
    path('update-claim-info/<uuid:claim_uuid>/',views.update_claim_details_view, name='update-claim-info'),
    path('delete-claim/<uuid:claim_uuid>/',views.delete_payment_claim, name='delete-claim'),

    # Line item Urls 
    path('claim-item/<uuid:item_uuid>/',views.ClaimLineItemDetailsView, name='claim-item'),
    path('update-line-item/<uuid:item_uuid>/',views.update_line_item, name='update-line-item'),
    path('add-line-item-evidence/<uuid:item_uuid>/',views.add_line_item_evidence, name='add-line-item-evidence'),

    path('delete-line-item-evidence/<uuid:item_uuid>/<int:attachment_id>/',views.delete_line_item_evidence, name='delete-line-item-evidence'),

    path('create-certified-item-amount/<uuid:item_uuid>/',views.create_certified_line_amount, name='create-certified-item-amount'),
    path('delete-certificate-attachment/<uuid:item_uuid>/<int:attachment_id>/',views.delete_certified_line_attachment, name='delete-certificate-attachment'),

    # Line Item Queries Urls 
    path('create-item-query/<uuid:item_uuid>/',views.create_line_item_query, name='create-item-query'),

    # Line Item Disputes Urls 
    path('line-item-disputes/<uuid:item_uuid>/',views.line_item_dispute_view, name='line-item-disputes'),

]
