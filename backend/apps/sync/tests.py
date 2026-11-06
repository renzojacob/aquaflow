"""
Feature B through HTTP: the rider's outbox arrives at POST /api/v1/rider/sync; the dispatcher
sees conflicts at /api/v1/dispatch/conflicts.
Run:  python manage.py test apps.sync
"""
import uuid
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import CustomerProfile
from apps.dispatch.models import Trip, Vehicle
from apps.dispatch.tests_trips import API, TripBase
from apps.inventory.models import StockLevel
from apps.orders.models import Order
from apps.sync.models import SyncAction, SyncConflict

SYNC = "/api/v1/rider/sync"


def act(action_type, *, order=None, trip=None, key=None, minutes_ago=5, **payload):
    """One outbox entry, as the phone would build it."""
    return {
        "idempotency_key": str(key or uuid.uuid4()),
        "action_type": action_type,
        "trip_id": trip.pk if trip else None,
        "order_id": order.pk if order else None,
        "device_time": (timezone.now() - timedelta(minutes=minutes_ago)).isoformat(),
        "payload": payload,
    }


class SyncTests(TripBase):
    def setUp(self):
        super().setUp()
        self.v = Vehicle.objects.create(name="Tricycle 1", plate="T1", capacity_containers=20)
        self.o1, self.o2, self.o3 = self.order(2), self.order(2), self.order(2)
        r = self.as_(self.dispatcher).post(f"{API}/trips", {
            "date": self.day.isoformat(), "period": "morning", "vehicle_id": self.v.pk,
            "order_ids": [self.o1.pk, self.o2.pk, self.o3.pk], "rider_id": self.rider.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.trip = Trip.objects.get(pk=r.data["id"])
        self.client.post(f"{API}/trips/{self.trip.pk}/approve")
        self.assertEqual(self.as_(self.rider).post(f"/api/v1/rider/trips/{self.trip.pk}/download").status_code, 200)

    def sync(self, *actions, user=None):
        r = self.as_(user or self.rider).post(SYNC, {"device_id": "phone-1", "actions": list(actions)}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        return [x["result"] for x in r.data["results"]], r.data["results"]

    def code(self, o):
        return Order.objects.get(pk=o.pk).confirmation_code

    def held(self, o):
        return CustomerProfile.objects.get(user=o.customer).containers_held

    # ---------- the demo day ----------
    def test_offline_day_applies_once_in_order(self):
        held_before = self.held(self.o1)
        batch = [
            act("start_trip", trip=self.trip, minutes_ago=60),
            act("deliver", order=self.o1, minutes_ago=40, code=self.code(self.o1), empties_collected=1),
            act("deliver", order=self.o2, minutes_ago=30, code=self.code(self.o2), empties_collected=0),
            act("fail", order=self.o3, minutes_ago=20, failure_reason="absent"),
            act("empties", order=self.o1, minutes_ago=10, count=1),
        ]
        results, _ = self.sync(*batch)
        self.assertEqual(results, ["applied"] * 5)
        self.assertEqual(Order.objects.get(pk=self.o1.pk).status, "delivered")
        self.assertEqual(Order.objects.get(pk=self.o3.pk).status, "failed")
        self.assertEqual(Trip.objects.get(pk=self.trip.pk).status, "completed")
        self.assertEqual(self.held(self.o1), held_before + 2 - 1 - 1)

        # The phone resends everything (lost the answer): nothing is applied twice
        results, out = self.sync(*batch)
        self.assertEqual(results, ["duplicate"] * 5)
        self.assertEqual(out[1]["original_result"], "applied")
        self.assertEqual(self.held(self.o1), held_before + 2 - 1 - 1)
        self.assertEqual(SyncAction.objects.count(), 5)

        # Device time is kept separately from the server's time
        sa = SyncAction.objects.get(action_type="deliver", order=self.o1)
        self.assertLess(sa.device_time, sa.server_time - timedelta(minutes=30))

        # The rider's Sync screen lists them
        rows = self.client.get(SYNC).data
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["result"] for r in rows}, {"applied"})

    # ---------- conflict rules ----------
    def test_out_of_order_is_rejected_then_retried_with_the_same_key(self):
        key = uuid.uuid4()
        deliver = act("deliver", order=self.o1, key=key, code=self.code(self.o1))
        results, out = self.sync(deliver)
        self.assertEqual(results, ["rejected"])
        self.assertIn("start trip", out[0]["error"])
        self.assertEqual(Order.objects.get(pk=self.o1.pk).status, "confirmed")

        # Phone kept it in the outbox; start arrives, the same key is sent again and now applies
        results, _ = self.sync(act("start_trip", trip=self.trip), deliver)
        self.assertEqual(results, ["applied", "applied"])
        self.assertEqual(Order.objects.get(pk=self.o1.pk).status, "delivered")
        self.assertEqual(SyncAction.objects.get(idempotency_key=key).result, "applied")

    def test_reassigned_trip_is_rejected_for_the_first_rider(self):
        self.as_(self.dispatcher).post(f"{API}/trips/{self.trip.pk}/assign", {"rider_id": self.rider2.pk}, format="json")
        results, out = self.sync(act("start_trip", trip=self.trip),
                                 act("deliver", order=self.o1, code=self.code(self.o1)))
        self.assertEqual(results, ["rejected", "rejected"])
        self.assertIn("another rider", out[0]["error"])
        self.assertEqual(SyncConflict.objects.count(), 0)

        # Order moved after the trip started: also rejected
        self.as_(self.rider2).post(f"/api/v1/rider/trips/{self.trip.pk}/download")
        self.sync(act("start_trip", trip=self.trip), user=self.rider2)
        results, out = self.sync(act("fail", order=self.o2, failure_reason="absent"))
        self.assertEqual(results, ["rejected"])
        self.assertIn("another rider", out[0]["error"])

    def test_cancelled_while_offline_delivery_is_kept_and_flagged(self):
        stock = StockLevel.objects.get(product=self.product)
        available, reserved = stock.filled_available, stock.filled_reserved
        held_before = self.held(self.o2)
        # The rider started offline (not synced yet), so the customer could still cancel
        r = self.as_(self.o2.customer).post(f"/api/customer/orders/{self.o2.pk}/cancel/", {"reason": "Changed my mind"}, format="json")
        self.assertIn(r.status_code, (200, 204), getattr(r, "data", None))
        self.assertEqual(Order.objects.get(pk=self.o2.pk).status, "cancelled")

        results, out = self.sync(
            act("start_trip", trip=self.trip, minutes_ago=50),
            act("deliver", order=self.o2, minutes_ago=30, code=self.code(self.o2), empties_collected=1,
                gps_lat=13.41, gps_lng=121.18, gps_accuracy_m=8),     # at the customer's pin
        )
        self.assertEqual(results, ["applied", "conflict"])
        self.assertEqual(out[1]["conflicts"], ["delivered_after_cancel"])
        o2 = Order.objects.get(pk=self.o2.pk)
        self.assertEqual(o2.status, "delivered")              # kept: the water was handed over
        self.assertTrue(o2.needs_review)
        self.assertEqual(self.held(self.o2), held_before + 2 - 1)
        stock.refresh_from_db()
        # o1 and o3 left from the reservation; o2's reservation was released by the cancel,
        # so its 2 containers came out of available stock
        self.assertEqual(stock.filled_reserved, reserved - 4 - 2)
        self.assertEqual(stock.filled_available, available + 2 - 2)

        # The dispatcher sees it in the queue and resolves it
        r = self.as_(self.dispatcher).get(f"{API}/conflicts")
        self.assertEqual(r.data["open_count"], 1)
        c = r.data["conflicts"][0]
        self.assertEqual((c["kind"], c["order"]["id"], c["action"]["rider"]["name"]), ("delivered_after_cancel", self.o2.pk, "Jomar"))
        self.assertNotIn("code", c["action"]["payload"])
        self.assertEqual(self.client.post(f"{API}/conflicts/{c['id']}/resolve", {}, format="json").status_code, 400)  # needs a note
        r = self.client.post(f"{API}/conflicts/{c['id']}/resolve", {"note": "Customer kept it and paid."}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["status"], "resolved")
        self.assertEqual(self.client.get(f"{API}/conflicts").data["open_count"], 0)
        self.assertEqual(len(self.client.get(f"{API}/conflicts", {"status": "resolved"}).data["conflicts"]), 1)
        self.assertFalse(Order.objects.get(pk=self.o2.pk).needs_review)
        self.assertEqual(self.client.post(f"{API}/conflicts/{c['id']}/resolve", {"note": "again"}, format="json").status_code, 400)

    def test_failing_a_cancelled_order_is_rejected(self):
        self.as_(self.o3.customer).post(f"/api/customer/orders/{self.o3.pk}/cancel/", {}, format="json")
        results, out = self.sync(act("start_trip", trip=self.trip), act("fail", order=self.o3, failure_reason="absent"))
        self.assertEqual(results, ["applied", "rejected"])
        self.assertIn("cancelled", out[1]["error"])

    def test_wrong_code_is_delivered_and_flagged(self):
        wrong = f"{(int(self.code(self.o1)) + 1) % 1_000_000:06d}"
        results, out = self.sync(act("start_trip", trip=self.trip), act("deliver", order=self.o1, code=wrong))
        self.assertEqual(results, ["applied", "conflict"])
        self.assertEqual(out[1]["conflicts"], ["code_mismatch"])
        self.assertEqual(Order.objects.get(pk=self.o1.pk).status, "delivered")
        self.assertEqual(self.as_(self.dispatcher).get(f"{API}/conflicts").data["conflicts"][0]["kind"], "code_mismatch")
        # No GPS was sent, so the delivery is also a geofence case: resolving the code
        # conflict must not hide that
        cid = self.client.get(f"{API}/conflicts").data["conflicts"][0]["id"]
        self.client.post(f"{API}/conflicts/{cid}/resolve", {"note": "Customer confirmed."}, format="json")
        self.assertTrue(Order.objects.get(pk=self.o1.pk).needs_review)

    def test_no_code_is_allowed_and_only_needs_review(self):
        results, _ = self.sync(act("start_trip", trip=self.trip),
                               act("deliver", order=self.o1, no_code=True, empties_collected=0))
        self.assertEqual(results, ["applied", "applied"])           # not a "wrong code" conflict
        o1 = Order.objects.get(pk=self.o1.pk)
        self.assertEqual((o1.status, o1.needs_review), ("delivered", True))
        self.assertEqual(SyncConflict.objects.count(), 0)
        results, out = self.sync(act("deliver", order=self.o2, code=self.code(self.o2), empties_collected=99))
        self.assertEqual(results, ["rejected"])
        self.assertIn("between 0 and 50", out[0]["error"])

    # ---------- bad input and safety ----------
    def test_bad_actions_are_rejected_one_by_one(self):
        good = act("start_trip", trip=self.trip)
        bad_key = {**act("start_trip", trip=self.trip), "idempotency_key": "not-a-uuid"}
        bad_type = act("teleport", order=self.o1)
        bad_time = {**act("deliver", order=self.o1), "device_time": "yesterday"}
        bad_id = act("deliver", order=self.o1); bad_id["order_id"] = "abc"
        no_order = act("deliver", code="123456")
        results, out = self.sync(bad_key, bad_type, bad_time, bad_id, no_order, good, "junk")
        self.assertEqual(results, ["rejected"] * 5 + ["applied", "rejected"])
        self.assertIn("UUID", out[0]["error"])
        self.assertIn("Unknown action", out[1]["error"])
        self.assertIn("device_time", out[2]["error"])
        self.assertIn("Order not found", out[4]["error"])

        r = self.as_(self.rider).post(SYNC, {"actions": "nope"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post(SYNC, {"actions": [good] * 201}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_another_riders_key_is_not_reused(self):
        key = uuid.uuid4()
        self.sync(act("start_trip", trip=self.trip, key=key))
        results, out = self.sync(act("start_trip", trip=self.trip, key=key), user=self.rider2)
        self.assertEqual(results, ["rejected"])
        self.assertIn("another rider", out[0]["error"])

    def test_empties_only_for_my_orders(self):
        other = self.order(2)
        results, _ = self.sync(act("start_trip", trip=self.trip), act("empties", order=other, count=1))
        self.assertEqual(results, ["applied", "rejected"])

    def test_permissions(self):
        self.assertEqual(self.as_(self.dispatcher).post(SYNC, {"actions": []}, format="json").status_code, 403)
        self.assertEqual(self.as_(self.rider).get(f"{API}/conflicts").status_code, 403)
        self.assertEqual(self.as_(self.dispatcher).get(f"{API}/conflicts", {"status": "maybe"}).status_code, 400)
