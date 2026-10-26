from django.db import transaction
from .models import StockLevel, StockMovement


@transaction.atomic
def apply_movement(product, reason, user=None, available=0, reserved=0, empty=0,
                   note="", order=None, trip=None):
    stock = StockLevel.objects.select_for_update().get(product=product)   # row lock
    stock.filled_available += available
    stock.filled_reserved += reserved
    stock.empty_count += empty
    stock.save()    # raises IntegrityError if any count would go below 0
    return StockMovement.objects.create(
        product=product, reason=reason, by_user=user, note=note, order=order,
        d_available=available, d_reserved=reserved, d_empty=empty, trip=trip
    )