from rest_framework import serializers

from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["customer", "is_archived"]
        read_only_fields = ["is_default", "address_text"]
        extra_kwargs = {
            "street": {"required": True, "allow_blank": False},
            "barangay": {"required": True, "allow_blank": False},
        }

    def validate(self, attrs):
        # address_text is what orders snapshot and riders read: "street, barangay"
        street = attrs.get("street", getattr(self.instance, "street", "")).strip()
        barangay = attrs.get("barangay", getattr(self.instance, "barangay", "")).strip()
        attrs["address_text"] = ", ".join(p for p in (street, barangay) if p)[:255]
        return attrs