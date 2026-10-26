from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsCustomer

from . import services
from .models import Address
from .serializers import AddressSerializer


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsCustomer]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return Address.objects.filter(
            customer=self.request.user, is_archived=False
        ).order_by("-is_default", "id")

    def perform_create(self, serializer):
        serializer.instance = services.create_address(
            self.request.user, **serializer.validated_data
        )

    def destroy(self, request, *args, **kwargs):
        services.archive_address(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=AddressSerializer)
    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        address = services.set_default_address(request.user, self.get_object())
        return Response(self.get_serializer(address).data)