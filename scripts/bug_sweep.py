import urllib.request, json, datetime, sys

base = "http://127.0.0.1:8000"

def get(path):
    try:
        with urllib.request.urlopen(base + path, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as ex:
        return 0, str(ex)

def post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            base + path, data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}
    except Exception as ex:
        return 0, str(ex)

bugs = []

def check(label, sc, data, expect_sc=200, check_fn=None):
    ok = sc == expect_sc
    if check_fn:
        ok = ok and check_fn(data)
    status = "OK " if ok else "BUG"
    if not ok:
        bugs.append((label, sc, data))
    print(f"  [{status}] {label} -> HTTP {sc}")
    if not ok:
        print(f"       data: {str(data)[:200]}")
    return ok, data

print("\n" + "="*55)
print("  SmartMandi Bug Sweep")
print("="*55)

# 1. Health
sc, d = get("/health")
check("GET /health", sc, d, 200, lambda x: x.get("status") == "online")

# 2. Centers
sc, centers = get("/centers")
ok, _ = check("GET /centers", sc, centers, 200, lambda x: len(x) > 0)

# 3. Farmers list
sc, farmers = get("/farmers?limit=5")
check("GET /farmers", sc, farmers, 200, lambda x: len(x) > 0)

# 4. Farmer by phone (existing)
phone = farmers[0]["phone_number"] if farmers else "0000000000"
fid   = farmers[0]["id"] if farmers else 1
sc, d = get(f"/api/farmers/by-phone/{phone}")
check("GET /api/farmers/by-phone/{phone}", sc, d, 200, lambda x: "id" in x)

# 5. Farmer by phone (unknown) - expect 404
sc, d = get("/api/farmers/by-phone/9999999999")
check("GET /api/farmers/by-phone/unknown -> 404", sc, d, 404)

# 6. Farmer bookings
sc, d = get(f"/api/farmers/{fid}/bookings")
check(f"GET /api/farmers/{fid}/bookings", sc, d, 200, lambda x: isinstance(x, list))

# 7. Center availability today
today = str(datetime.date.today())
cid = centers[0]["id"] if centers else 1
sc, d = get(f"/api/farmers/centers/{cid}/availability?booking_date={today}")
check("GET /api/farmers/centers/1/availability", sc, d, 200,
      lambda x: "remaining_quintals" in x and "is_available" in x)

# 8. New booking
sc, d = post("/api/bookings", {
    "farmer_id": fid, "center_id": cid,
    "crop_type": "Wheat (Kanak)",
    "estimated_quantity_quintals": 75.0,
    "requested_date": today
})
check("POST /api/bookings", sc, d, 201, lambda x: "queue_number" in x)

# 9. Bookings list
sc, bk = get("/bookings")
check("GET /bookings", sc, bk, 200, lambda x: isinstance(x, list))

# 10. Register new farmer (fresh phone)
import random
fake_phone = "8" + str(random.randint(100000000, 999999999))
sc, d = post("/api/farmers/register", {
    "name": "Test Farmer", "phone_number": fake_phone,
    "village": "Testpur", "district": "Karnal",
    "state": "Haryana", "has_linked_bank_account": False
})
check("POST /api/farmers/register (new)", sc, d, 201, lambda x: "id" in x)

# 11. Duplicate phone register - expect 409
sc, d = post("/api/farmers/register", {
    "name": "Duplicate", "phone_number": phone,
    "district": "Karnal", "state": "Haryana",
    "has_linked_bank_account": False
})
check("POST /api/farmers/register (duplicate) -> 409", sc, d, 409)

# 12. Status update on a booking
if isinstance(bk, list) and bk:
    active_b = [b for b in bk if b.get("status") in ("CONFIRMED",)]
    if active_b:
        bid = active_b[0]["id"]
        body = json.dumps({"status": "CHECKED_IN"}).encode()
        req = urllib.request.Request(
            f"{base}/api/bookings/{bid}/status",
            data=body, headers={"Content-Type": "application/json"}, method="PATCH"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                sc2, d2 = r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try: sc2, d2 = e.code, json.loads(e.read())
            except: sc2, d2 = e.code, {}
        check(f"PATCH /api/bookings/{bid}/status -> CHECKED_IN", sc2, d2, 200,
              lambda x: x.get("new_status") == "CHECKED_IN")
    else:
        print("  [SKIP] No CONFIRMED booking available for status-update test")

print()
print("="*55)
if bugs:
    print(f"  BUGS FOUND: {len(bugs)}")
    for i, (label, sc, data) in enumerate(bugs, 1):
        print(f"  Bug #{i}: {label}")
        print(f"    HTTP {sc} => {str(data)[:300]}")
else:
    print("  ALL CHECKS PASSED - No bugs found in backend!")
print("="*55)
