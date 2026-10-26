from django.db import transaction

from .models import CustomerProfile, User


@transaction.atomic
def register_customer(*, username, password, email, phone, first_name="", last_name=""):
    user = User(
        username=username,
        email=email,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        role="customer",
    )
    user.set_password(password)
    user.save()
    CustomerProfile.objects.get_or_create(user=user)
    return user