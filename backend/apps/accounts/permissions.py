from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    allowed_roles: tuple[str, ...] = ()
    message = "Your account role cannot use this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in self.allowed_roles
        )


class IsCustomer(HasRole):
    allowed_roles = ("customer",)


class IsDispatcher(HasRole):
    allowed_roles = ("dispatcher",)


class IsRider(HasRole):
    allowed_roles = ("rider",)


class IsOwner(HasRole):
    allowed_roles = ("owner",)


class IsDispatcherOrOwner(HasRole):
    allowed_roles = ("dispatcher", "owner")