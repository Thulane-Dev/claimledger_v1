from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(PaymentClaimModel)
admin.site.register(PaymentClaimLineItemModel)
admin.site.register(ClaimQueryModel)
admin.site.register(ClaimQueryResponseModel)
admin.site.register(ClaimCertificationAttachmentModel)
admin.site.register(QueriesResponsesAttachmentModel)
