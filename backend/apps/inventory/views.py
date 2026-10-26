from rest_framework import viewsets

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        # If Product has an is_active field, use:
        # return Product.objects.filter(is_active=True).order_by("id")
        return Product.objects.all().order_by("id")