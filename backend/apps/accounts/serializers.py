from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from .models import CustomerProfile, User


def _profile(user):
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    return profile


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["reminders_enabled", "usual_quantity", "containers_held"]
        read_only_fields = ["containers_held"]


class MeSerializer(serializers.ModelSerializer):
    """The user object the frontend keeps in its auth store."""

    full_name = serializers.SerializerMethodField()
    containers_held = serializers.SerializerMethodField()
    customer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "role", "full_name", "first_name", "last_name",
            "username", "email", "phone", "containers_held", "customer_profile",
        ]
        read_only_fields = ["id", "role", "username"]

    def get_full_name(self, user) -> str:
        return user.get_full_name() or user.username

    def get_containers_held(self, user) -> int | None:
        return _profile(user).containers_held if user.role == "customer" else None

    @extend_schema_field(CustomerProfileSerializer(allow_null=True))
    def get_customer_profile(self, user):
        if user.role != "customer":
            return None
        return CustomerProfileSerializer(_profile(user)).data

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if value and qs.exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class LoginSerializer(serializers.Serializer):
    """The app sends `email`, but staff may also type their username."""

    email = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        login = attrs["email"].strip()
        match = (
            User.objects.filter(email__iexact=login).first()
            or User.objects.filter(username__iexact=login).first()
        )
        user = None
        if match:
            user = authenticate(
                request=self.context.get("request"),
                username=match.username,
                password=attrs["password"],
            )
        if user is None or not user.is_active:
            raise AuthenticationFailed("Wrong email or password.")
        attrs["user"] = user
        return attrs


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_full_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Enter your name.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if (
            User.objects.filter(email__iexact=value).exists()
            or User.objects.filter(username__iexact=value).exists()
        ):
            raise serializers.ValidationError(
                "An account with this email already exists. Try logging in."
            )
        return value

    def validate(self, attrs):
        candidate = User(username=attrs["email"], email=attrs["email"],
                         first_name=attrs["full_name"])
        validate_password(attrs["password"], user=candidate)
        return attrs