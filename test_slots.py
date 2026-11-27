import requests
from datetime import datetime, timedelta

# Login as doctor
resp = requests.post("http://localhost:8000/auth/login", data={"username": "dr.shintre@trimurticlinic.com", "password": "password123"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get doctor me
me_resp = requests.get("http://localhost:8000/users/me", headers=headers)
print("Me:", me_resp.json())

# Update working hours
config = {
    "slot_duration_minutes": 20,
    "schedule": {
        "monday": {"start": "09:00", "end": "17:00"},
        "saturday": {"start": "09:00", "end": "12:00"},
        "sunday": {"start": "10:00", "end": "14:00"}
    }
}
patch_resp = requests.patch("http://localhost:8000/doctors/me/working-hours", json=config, headers=headers)
print("Patch hours:", patch_resp.json())

# Generate slots for next saturday
today = datetime.now()
days_ahead = 5 - today.weekday() # Saturday
if days_ahead <= 0:
    days_ahead += 7
next_saturday = (today + timedelta(days=days_ahead)).strftime("%Y-%M-%d")
print("Next Saturday:", next_saturday)

# Wait, let's just generate for 2026-10-03 (Saturday)
gen_resp = requests.post(f"http://localhost:8000/doctors/1/slots/generate?target_date=2026-10-03", headers=headers)
print("Generate Saturday:", gen_resp.json())

# Check open slots
slots_resp = requests.get("http://localhost:8000/slots?doctor_id=1&date=2026-10-03", headers=headers)
print("Slots on Saturday:", len(slots_resp.json()))

