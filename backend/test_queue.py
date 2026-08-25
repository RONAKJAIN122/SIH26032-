import urllib.request
import json
from datetime import date

BASE = "http://127.0.0.1:8000"

def http_req(url, method="GET", data=None):
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

status_f, farmers = http_req(f"{BASE}/farmers")
farmer2 = farmers[1]
phone = farmer2["phone_number"]
name = farmer2["name"]

book_payload = {
    "farmer_id": farmer2["id"],
    "center_id": 1,
    "crop_type": "Wheat (Kanak)",
    "estimated_quantity_quintals": 75.0,
    "requested_date": str(date.today())
}
http_req(f"{BASE}/api/bookings", method="POST", data=book_payload)

s, r = http_req(f"{BASE}/api/farmers/{phone}/active-booking")
print(f"Farmer {name} ({phone}) Active Booking Query Status: {s}")
print(json.dumps(r, indent=2))
