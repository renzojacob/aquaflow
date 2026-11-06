"""
Feature C: recompute every household's refill prediction from its delivered orders.

    python manage.py rebuild_refill_predictions

Predictions normally refresh by themselves after each delivery. Run this once after
deploying Feature C (to cover deliveries made before it existed), or after correcting
old orders by hand.
"""
from django.core.management.base import BaseCommand

from apps.predictions.services import rebuild_all


class Command(BaseCommand):
    help = "Recompute refill predictions for every household from its delivered orders."

    def handle(self, *args, **opts):
        made, skipped = rebuild_all()
        self.stdout.write(self.style.SUCCESS(
            f"{made} household(s) predicted, {skipped} without enough history yet."))
