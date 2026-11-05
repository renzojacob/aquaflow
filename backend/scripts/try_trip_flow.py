"""
Walk the whole trip flow against a RUNNING server, the same way the apps call it.

    cd backend
    python manage.py seed_trip_demo            # demo accounts + 3 confirmed orders for tomorrow
    python manage.py runserver                 # in another terminal
    python scripts/try_trip_flow.py            # or: --base http://127.0.0.1:8000 --period morning

Only the Python standard library is used. Each step prints PASS/FAIL; the script stops at
the first failure and shows the server's answer. Run seed_trip_demo again before each run.
"""
import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

PASSWORD = "Demo2026!x"
DISPATCHER = "demo.dispatcher@aquaflow.test"
RIDER = "demo.rider@aquaflow.test"
RIDER2 = "demo.rider2@aquaflow.test"

BASE = "http://127.0.0.1:8000"
step_no = 0


def call(method, path, token=None, body=None):
    """-> (status, json or None)"""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else None
        except ValueError:
            return e.code, raw.decode(errors="replace")[:300]
    except urllib.error.URLError as e:
        sys.exit(f"Can't reach {BASE}: {e.reason}. Is `python manage.py runserver` running?")


def step(title, status, body, expect, check=None):
    """Print one numbered step; stop the script if the status or the extra check is wrong."""
    global step_no
    step_no += 1
    ok = status == expect and (check is None or check(body))
    print(f"{'PASS' if ok else 'FAIL'}  {step_no:>2}. {title}  [{status}]")
    if not ok:
        print(f"      expected HTTP {expect}. Server answered:")
        print("      " + json.dumps(body, indent=2, default=str)[:1500].replace("\n", "\n      "))
        sys.exit(1)
    return body


def login(email):
    status, body = call("POST", "/api/auth/login/", body={"email": email, "password": PASSWORD})
    if status == 429:
        sys.exit("Login is limited to 10 tries a minute (each run logs in 6 times). Wait a minute and run again.")
    if status != 200:
        sys.exit(f"Login failed for {email} [{status}]: {body}\nRun `python manage.py seed_trip_demo` first.")
    return body["token"]


def main():
    global BASE
    p = argparse.ArgumentParser()
    p.add_argument("--base", default=BASE)
    p.add_argument("--period", default="morning", choices=["morning", "afternoon"])
    a = p.parse_args()
    BASE = a.base.rstrip("/")
    day = (date.today() + timedelta(days=1)).isoformat()
    q = f"?date={day}&period={a.period}"

    disp, rider, rider2 = login(DISPATCHER), login(RIDER), login(RIDER2)
    print(f"Logged in as dispatcher and two riders. Slot: {day} {a.period}\n")

    # ---------------- Dispatcher builds the trip ----------------
    print("Dispatcher")
    vehicles = step("List vehicles", *call("GET", f"/api/v1/dispatch/vehicles{q}", disp), 200)
    trike = next((v for v in vehicles if v["plate"] == "DEMO-001"), None)
    bike = next((v for v in vehicles if v["plate"] == "DEMO-002"), None)
    if not trike or not bike:
        sys.exit("Demo vehicles missing. Run `python manage.py seed_trip_demo`.")

    board = step("List trips + unplanned orders", *call("GET", f"/api/v1/dispatch/trips{q}", disp), 200,
                 lambda b: len([o for o in b["unplanned"] if o["customer_name"].startswith("Demo")]) >= 3)
    demo = [o for o in board["unplanned"] if o["customer_name"].startswith("Demo")][-3:]
    ids = [o["order_id"] for o in demo]
    print(f"      using orders {', '.join('AF-%d' % i for i in ids)}")

    step(f"Too much for the bike ({sum(o['containers'] for o in demo)} containers on {bike['capacity']}) is refused",
         *call("POST", "/api/v1/dispatch/trips", disp,
               {"date": day, "period": a.period, "vehicle_id": bike["id"], "order_ids": ids}), 400)

    trip = step("Create draft trip on the tricycle with 2 orders",
                *call("POST", "/api/v1/dispatch/trips", disp,
                      {"date": day, "period": a.period, "vehicle_id": trike["id"], "order_ids": ids[:2]}),
                201, lambda b: b["status"] == "draft" and len(b["stops"]) == 2)
    tid = trip["id"]
    print(f"      Trip #{tid}: load {trip['load']['departure']}/{trip['load']['capacity']}, "
          f"~{trip['total_distance_m']} m (estimate)")

    step("Same order on a second trip is refused",
         *call("POST", "/api/v1/dispatch/trips", disp,
               {"date": day, "period": a.period, "vehicle_id": bike["id"], "order_ids": ids[:1]}), 400)

    order_now = [ids[2], ids[1], ids[0]]
    trip = step("Edit stops: add the 3rd order and reverse the order",
                *call("PUT", f"/api/v1/dispatch/trips/{tid}/stops", disp, {"order_ids": order_now}),
                200, lambda b: [s["order_id"] for s in b["stops"]] == order_now and b["version"] == 2)
    for s in trip["stops"]:
        print(f"      stop {s['sequence']}: AF-{s['order_id']} {s['barangay']:<10} load after {s['expected_load_after']}")

    step("Assign Demo Rider",
         *call("POST", f"/api/v1/dispatch/trips/{tid}/assign", disp,
               {"rider_id": _rider_id(disp, "Demo Rider")}), 200, lambda b: b["rider"] is not None)

    # ---------------- Rider before approval ----------------
    print("\nRider (before approval)")
    step("Draft trip is not in the rider's list",
         *call("GET", "/api/v1/rider/trips", rider), 200, lambda b: tid not in [t["id"] for t in b])
    step("Downloading a draft is refused", *call("POST", f"/api/v1/rider/trips/{tid}/download", rider), 400)

    print("\nDispatcher")
    step("Approve the trip", *call("POST", f"/api/v1/dispatch/trips/{tid}/approve", disp), 200,
         lambda b: b["status"] == "approved")
    # (approved trips can still be edited on main: live re-planning)

    # ---------------- Rider downloads and starts ----------------
    print("\nRider")
    step("Approved trip shows in my list", *call("GET", "/api/v1/rider/trips", rider), 200,
         lambda b: tid in [t["id"] for t in b])
    dl = step("Download the trip", *call("POST", f"/api/v1/rider/trips/{tid}/download", rider), 200,
              lambda b: b["status"] == "downloaded" and len(b["stops"]) == 3)

    codes = {i: _customer_code(i) for i in ids}
    raw = json.dumps(dl)
    step("Download has hashed codes only (no plain code anywhere)", 200,
         {"stops": [{k: s[k] for k in ("id", "code_salt", "code_hash")} for s in dl["stops"]]}, 200,
         lambda _: all(f'"{c}"' not in raw for c in codes.values())
         and all("confirmation_code" not in s for s in dl["stops"]))
    step("Offline check: sha256('<salt>:<code>') matches each stop's hash", 200, None, 200,
         lambda _: all(hashlib.sha256(f"{s['code_salt']}:{codes[s['id']]}".encode()).hexdigest() == s["code_hash"]
                       for s in dl["stops"]))
    step("Offline check: a wrong code does NOT match", 200, None, 200,
         lambda _: hashlib.sha256(f"{dl['stops'][0]['code_salt']}:000000".encode()).hexdigest()
         != dl["stops"][0]["code_hash"] or codes[dl["stops"][0]["id"]] == "000000")

    print("\nRules")
    step("Dispatcher can't send a trip order out directly",
         *call("POST", f"/api/v1/dispatch/orders/{ids[0]}/dispatch", disp, {}), 400)
    step("Another rider can't start this trip", *call("POST", f"/api/v1/rider/trips/{tid}/start", rider2), 404)

    print("\nRider on the road")
    step("Start the trip", *call("POST", f"/api/v1/rider/trips/{tid}/start", rider, {}), 200, lambda b: b["status"] == "out")
    step("Starting twice is refused", *call("POST", f"/api/v1/rider/trips/{tid}/start", rider), 400)
    step("Today's stops follow the trip order", *call("GET", "/api/v1/rider/today", rider), 200,
                 lambda b: [s["id"] for s in b["stops"] if s["id"] in ids] == order_now)

    first, second, third = order_now
    step("Wrong code is refused", *call("POST", f"/api/v1/rider/orders/{first}/deliver", rider,
                                        {"code": _wrong(codes[first]), "empties_collected": 1}), 400)
    step(f"Deliver AF-{first} with the right code",
         *call("POST", f"/api/v1/rider/orders/{first}/deliver", rider,
               {"code": codes[first], "empties_collected": 1}), 200)
    step(f"Deliver AF-{second}",
         *call("POST", f"/api/v1/rider/orders/{second}/deliver", rider,
               {"code": codes[second], "empties_collected": 1}), 200)
    step(f"Fail AF-{third} (no one home)",
         *call("POST", f"/api/v1/rider/orders/{third}/fail", rider, {"failure_reason": "absent"}), 200)

    print("\nDispatcher after the trip")
    step("Trip is completed with 2 done and 1 failed stop",
         *call("GET", f"/api/v1/dispatch/trips/{tid}", disp), 200,
         lambda b: b["status"] == "completed"
         and sorted(s["status"] for s in b["stops"]) == ["done", "done", "failed"])
    step("Can't re-assign a completed trip",
         *call("POST", f"/api/v1/dispatch/trips/{tid}/assign", disp,
               {"rider_id": _rider_id(disp, "Demo Rider Two")}), 400)

    print(f"\nAll {step_no} steps passed. Trip #{tid} went draft -> approved -> downloaded -> out -> completed.")
    print("Run `python manage.py seed_trip_demo` again before the next run.")


# ---------------- helpers ----------------
def _rider_id(disp, name):
    status, riders = call("GET", "/api/v1/dispatch/riders", disp)
    match = [r for r in riders if r["name"] == name] if status == 200 else []
    if not match:
        sys.exit(f"Rider '{name}' not found. Run `python manage.py seed_trip_demo`.")
    return match[0]["id"]


_customer_tokens = {}


def _customer_code(order_id):
    """The code the customer sees in their app (that's what the rider asks for at the door)."""
    for name in ("ana", "ben", "cora"):
        email = f"demo.{name}@aquaflow.test"
        if email not in _customer_tokens:
            _customer_tokens[email] = login(email)
        status, body = call("GET", f"/api/customer/orders/{order_id}/", _customer_tokens[email])
        if status == 200:
            return body["confirmation_code"]
    sys.exit(f"Couldn't read the code for AF-{order_id} as its customer.")


def _wrong(code):
    return f"{(int(code) + 1) % 1_000_000:06d}"


if __name__ == "__main__":
    main()
