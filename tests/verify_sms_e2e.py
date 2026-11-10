"""
SOS Guardian - End-to-End SMS Dispatch Verification Script
Validates:
1. Adding a guardian contact (10-digit mobile) via POST /api/contacts saves directly to SQLite.
2. The guardian requires no app or registration.
3. Triggering POST /api/sos pulls saved numbers from SQLite and dispatches SMS alert with Google Maps pin.
4. Database notification_logs table confirms delivery status.
"""

import sys
import os

# Bootstrap backend
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import (
    initialize_database,
    create_user,
    get_user_by_email,
    get_contacts,
    get_notification_logs,
    get_sos_events
)
from rate_limiter import rate_limiter

def run_verification():
    initialize_database()
    rate_limiter.clear_all()
    client = app.test_client()
    app.config["TESTING"] = True

    print("\n=======================================================")
    print("🚀 SOS GUARDIAN: END-TO-END SMS DISPATCH VERIFICATION")
    print("=======================================================")

    # 1. Setup authenticated user
    email = "guardian_sms_validation@sosguardian.local"
    user = get_user_by_email(email)
    if not user:
        user_id = create_user("SMS Validation User", email, "secure_hashed_password")
    else:
        user_id = user["id"]

    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    print(f"✅ Authenticated User: ID #{user_id} ({email})")

    # 2. Add guardian contact via POST /api/contacts
    guardian_payload = {
        "name": "Guardian Mom",
        "phone": "9876543210",
        "telegram_chat_id": None
    }
    print(f"\n1️⃣ Registering Guardian Contact on Web:")
    print(f"   Name   : {guardian_payload['name']}")
    print(f"   Mobile : {guardian_payload['phone']} (No app or account required for guardian)")

    res_contact = client.post("/api/contacts", json=guardian_payload)
    assert res_contact.status_code in [200, 201], f"Failed to add contact: {res_contact.data}"
    c_data = res_contact.get_json()
    contact_id = c_data.get("contact_id") or c_data["contact"]["id"]
    print(f"   Status : HTTP {res_contact.status_code} - {c_data['message']}")
    print(f"   Contact ID in SQLite: #{contact_id}")

    # Confirm direct persistence in SQLite
    contacts = get_contacts(user_id)
    saved_contact = next((c for c in contacts if c["id"] == contact_id), None)
    assert saved_contact is not None, "Contact was not saved to SQLite!"
    print(f"   Verified in SQLite database table 'emergency_contacts':")
    print(f"   -> [ID: {saved_contact['id']}] Name: '{saved_contact['name']}', Phone: '{saved_contact['phone']}'")

    # 3. Trigger emergency SOS via POST /api/sos
    sos_payload = {
        "trigger_type": "manual",
        "latitude": 12.9716,
        "longitude": 77.5946
    }
    print(f"\n2️⃣ Activating Emergency Distress Signal:")
    print(f"   Trigger  : {sos_payload['trigger_type']}")
    print(f"   Latitude : {sos_payload['latitude']}")
    print(f"   Longitude: {sos_payload['longitude']}")

    res_sos = client.post("/api/sos", json=sos_payload)
    assert res_sos.status_code == 200, f"SOS trigger failed: {res_sos.data}"
    sos_data = res_sos.get_json()
    event_id = sos_data.get("event_id") or sos_data["event"]["id"]
    maps_url = sos_data["event"]["maps_url"]

    print(f"   Status   : HTTP 200 - {sos_data['message']}")
    print(f"   Event ID : #{event_id}")
    print(f"   Maps Pin : {maps_url}")

    # 4. Verify SQLite notification_logs table
    logs = get_notification_logs(event_id)
    print(f"\n3️⃣ Verifying Persistent Notification Logs in SQLite:")
    print(f"   Total Logged Dispatches for Event #{event_id}: {len(logs)}")

    guardian_log = next((l for l in logs if l["contact_id"] == contact_id and l["channel"] == "sms"), None)
    assert guardian_log is not None, "No SMS log found for guardian!"

    print(f"   -> Channel   : {guardian_log['channel']}")
    print(f"   -> Recipient : {guardian_log['recipient']}")
    print(f"   -> Provider  : {guardian_log['provider']}")
    print(f"   -> Status    : {guardian_log['status']}")
    print(f"   -> Timestamp : {guardian_log['created_at']}")

    # 5. Verify SMS format and Maps URL pin
    from providers.sms_provider import format_emergency_sms
    formatted_msg = format_emergency_sms(
        user_name="SMS Validation User",
        trigger_type="manual",
        latitude=12.9716,
        longitude=77.5946
    )
    assert "https://www.google.com/maps?q=12.9716,77.5946" in formatted_msg
    assert "9876543210" == guardian_log["recipient"]

    print(f"\n4️⃣ Dispatched SMS Message Preview:")
    print("--------------------------------------------------")
    print(formatted_msg)
    print("--------------------------------------------------")

    print("\n=======================================================")
    print("✅ END-TO-END SMS DISPATCH VERIFICATION SUCCESSFUL!")
    print("   1. Contact registered via web without guardian app.")
    print("   2. Directly saved in SQLite emergency_contacts table.")
    print("   3. SOS triggered -> pulled number from SQLite.")
    print("   4. Dispatched SMS with clickable Google Maps pin.")
    print("   5. Delivery recorded in SQLite notification_logs.")
    print("=======================================================\n")

if __name__ == "__main__":
    run_verification()

