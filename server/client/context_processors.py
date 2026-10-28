from authentication.models import UserModel
from django.db.models import Prefetch

def company_context(request):
    if request.user.is_authenticated:
        try:
            current_user = UserModel.objects.get(user=request.user)

            return {
                "company": current_user.company
            }

        except UserModel.DoesNotExist:
            pass

    return {
        "company": None
    }
