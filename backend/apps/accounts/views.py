from django.contrib.auth.models import update_last_login
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import CustomerProfile
from .permissions import IsCustomer
from .serializers import (
    CustomerProfileSerializer, LoginSerializer, MeSerializer, RegisterSerializer,
)


def session_payload(user):
    """Shape the frontend expects: {token, refresh, user}."""
    refresh = RefreshToken.for_user(user)
    return {
        "token": str(refresh.access_token),
        "refresh": str(refresh),
        "user": MeSerializer(user).data,
    }


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # an old token in the header must not block login
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        update_last_login(None, user)
        return Response(session_payload(user))


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale token in the header must not block signup
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=RegisterSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        first, _, last = data["full_name"].partition(" ")
        user = services.register_customer(
            username=data["email"],      # the email doubles as the username
            password=data["password"],
            email=data["email"],
            phone=data["phone"],
            first_name=first,
            last_name=last,
        )
        return Response(session_payload(user), status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsCustomer]
    http_method_names = ["get", "patch"]

    def get_object(self):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        return profile