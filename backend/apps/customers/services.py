from django.db import transaction
from django.db.models import F
from apps.accounts.models import CustomerProfile
from .models import ContainerMovement


@transaction.atomic
def record_containers(customer, delivered=0, returned=0, note="", order=None):
    profile, _ = CustomerProfile.objects.get_or_create(user=customer)
    CustomerProfile.objects.filter(pk=profile.pk).update(
        containers_held=F("containers_held") + delivered - returned
    )
    return ContainerMovement.objects.create(
        customer=customer, delivered=delivered, returned=returned, note=note, order=order
    )