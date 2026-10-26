from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer"
        DISPATCHER = "dispatcher"
        RIDER = "rider"
        OWNER = "owner"
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)

from django.conf import settings

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="customer_profile")
    reminders_enabled = models.BooleanField(default=True)
    usual_quantity = models.PositiveSmallIntegerField(default=1)
    containers_held = models.IntegerField(default=0)  # cached balance, updated from ContainerMovement

    def __str__(self):
        return f"Customer: {self.user.username}"


class RiderProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="rider_profile")
    default_vehicle = models.ForeignKey("dispatch.Vehicle", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"Rider: {self.user.username}"
