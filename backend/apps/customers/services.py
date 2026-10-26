from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Address
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

def _lock_customer(customer):
    get_user_model().objects.select_for_update().get(pk=customer.pk)


@transaction.atomic
def create_address(customer, **data):
    _lock_customer(customer)
    data.pop("is_default", None)
    has_default = Address.objects.filter(customer=customer, is_default=True).exists()
    return Address.objects.create(customer=customer, is_default=not has_default, **data)


@transaction.atomic
def set_default_address(customer, address):
    _lock_customer(customer)
    address = Address.objects.select_for_update().get(
        pk=address.pk, customer=customer, is_archived=False
    )
    # Unset the old default first so the partial unique constraint never sees two.
    Address.objects.filter(customer=customer, is_default=True).exclude(
        pk=address.pk
    ).update(is_default=False)
    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default"])
    return address


@transaction.atomic
def archive_address(customer, address):
    _lock_customer(customer)
    address = Address.objects.select_for_update().get(pk=address.pk, customer=customer)
    was_default = address.is_default
    address.is_archived = True
    address.is_default = False
    address.save(update_fields=["is_archived", "is_default"])

    if was_default:
        nxt = (
            Address.objects.select_for_update()
            .filter(customer=customer, is_archived=False)
            .order_by("id")
            .first()
        )
        if nxt:
            nxt.is_default = True
            nxt.save(update_fields=["is_default"])