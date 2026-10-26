from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            exc = DRFValidationError(exc.message_dict)
        else:
            exc = DRFValidationError({"detail": exc.messages})
    return exception_handler(exc, context)