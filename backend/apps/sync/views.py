"""
Feature B endpoints.

Rider (IsRider), mounted under /api/v1/rider/:
  POST sync     {device_id, actions: [{idempotency_key, action_type, trip_id?, order_id?,
                                       payload, device_time}]}
                -> {server_time, results: [{idempotency_key, result, error, conflicts?}]}
                Actions are applied in the order sent, each in its own transaction, so one bad
                action never blocks the rest. See sync/services.py for what each result means.
  GET  sync     my last 50 synced actions (for the rider's Sync screen)

Dispatcher or owner, mounted under /api/v1/dispatch/:
  GET  conflicts?status=open|resolved|all     the conflict queue (default: open)
  POST conflicts/<id>/resolve  {note}         mark it handled
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsDispatcherOrOwner, IsRider

from . import services
from .models import SyncAction, SyncConflict

MAX_ACTIONS = 200

ACTION_LABEL = {
    "start_trip": "Start trip",
    "deliver": "Delivered",
    "fail": "Couldn't deliver",
    "empties": "Empties collected",
}

# What the dispatcher reads in the queue, and what to check
KIND_HELP = {
    "delivered_after_cancel": (
        "Delivered after the customer cancelled",
        "The customer cancelled while the rider had no signal, and the rider handed the water over. "
        "The delivery was kept. Call the customer about payment and the containers."),
    "code_mismatch": (
        "Wrong delivery code",
        "The rider entered a code that doesn't match the customer's. The delivery was recorded. "
        "Check with the customer that they received it."),
    "reassigned": (
        "Order belonged to another rider",
        "The order had been moved to another rider when this action arrived."),
    "out_of_order": (
        "Action arrived out of order",
        "The order wasn't in a state where this action could apply."),
}


def _name(u):
    return (u.get_full_name() or u.username) if u else None


def _safe_payload(sa):
    """Payload for display, without the code the rider typed."""
    return {k: v for k, v in (sa.payload or {}).items() if k != "code"}


class RiderSyncView(APIView):
    permission_classes = [IsRider]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        actions = request.data.get("actions")
        if not isinstance(actions, list):
            raise ValidationError({"actions": ["Send a list of actions."]})
        if len(actions) > MAX_ACTIONS:
            raise ValidationError({"actions": [f"Send at most {MAX_ACTIONS} actions at a time."]})
        device_id = str(request.data.get("device_id") or "unknown")[:100]
        results = services.apply_batch(request.user, device_id, actions)
        return Response({"server_time": timezone.now().isoformat(), "results": results})

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        rows = (SyncAction.objects.filter(rider=request.user)
                .prefetch_related("conflicts").order_by("-server_time")[:50])
        return Response([{
            "idempotency_key": str(sa.idempotency_key),
            "action_type": sa.action_type,
            "label": ACTION_LABEL.get(sa.action_type, sa.action_type),
            "trip_id": sa.trip_id,
            "order_id": sa.order_id,
            "result": sa.result,
            "error": sa.error,
            "conflicts": [c.kind for c in sa.conflicts.all()],
            "device_time": sa.device_time.isoformat(),
            "server_time": sa.server_time.isoformat(),
        } for sa in rows])


def conflict_row(c):
    sa = c.sync_action
    title, help_text = KIND_HELP.get(c.kind, (c.kind, ""))
    o = c.order
    return {
        "id": c.id,
        "kind": c.kind,
        "title": title,
        "help": help_text,
        "status": c.status,
        "created_at": c.created_at.isoformat(),
        "order": ({
            "id": o.pk, "code": f"AF-{o.pk}", "status": o.status,
            "customer_name": _name(o.customer), "address": o.address_text,
            "containers": o.containers, "total": str(o.total),
            "cancel_reason": o.cancel_reason,
        } if o else None),
        "action": {
            "type": sa.action_type,
            "label": ACTION_LABEL.get(sa.action_type, sa.action_type),
            "rider": {"id": sa.rider_id, "name": _name(sa.rider)},
            "device_time": sa.device_time.isoformat(),      # when it happened on the phone
            "server_time": sa.server_time.isoformat(),      # when it reached the server
            "payload": _safe_payload(sa),
        },
        "resolved_by": _name(c.resolved_by),
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "resolution_note": c.resolution_note,
    }


def _conflicts():
    return SyncConflict.objects.select_related(
        "sync_action__rider", "order__customer", "resolved_by")


class ConflictListView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        status = request.query_params.get("status", "open")
        qs = _conflicts()
        if status in SyncConflict.Status.values:
            qs = qs.filter(status=status)
        elif status != "all":
            raise ValidationError({"status": ["Use open, resolved or all."]})
        return Response({
            "open_count": SyncConflict.objects.filter(status=SyncConflict.Status.OPEN).count(),
            "conflicts": [conflict_row(c) for c in qs[:200]],
        })


class ConflictResolveView(APIView):
    permission_classes = [IsDispatcherOrOwner]

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request, pk):
        c = services.resolve_conflict(get_object_or_404(SyncConflict, pk=pk), request.user,
                                      request.data.get("note"))
        return Response(conflict_row(_conflicts().get(pk=c.pk)))
