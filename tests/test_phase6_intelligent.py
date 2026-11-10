"""
SOS Guardian - Intelligent Emergency Features Test Suite
Phase 6 Automated Verification:
1. Fall Detection SOS trigger modality.
2. Continuous live location tracking & breadcrumbs streaming.
3. Live emergency tracking view endpoint (/api/sos/<id>/tracking).
4. Multi-contact emergency escalation protocol.
5. Guardian / responder emergency acknowledgement.
6. Safety check-in timer lifecycle (start, status, safe checkin).
7. Missed safety check-in automated emergency dispatch.
8. Contact priority tiers (Primary, Secondary, Backup).
"""

import os
import sys
import json
import unittest
from datetime import datetime

# Bootstrap sys.path for backend imports
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app
from database import (
    initialize_database,
    create_user,
    get_user_by_email,
    add_contact,
    get_contacts,
    get_contacts_by_priority,
    create_sos_event,
    get_sos_event_by_id,
    get_breadcrumbs,
    get_notification_logs,
    get_active_safety_checkin
)
from rate_limiter import rate_limiter


class TestPhase6IntelligentFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.client = app.test_client()
        app.config["TESTING"] = True

        # Test user
        cls.test_email = "phase6_tester@sosguardian.local"
        existing = get_user_by_email(cls.test_email)
        if not existing:
            cls.user_id = create_user("Phase 6 Tester", cls.test_email, "hashed_pw_phase6")
        else:
            cls.user_id = existing["id"]

        # Ensure tiered contacts exist (Tier 1 Primary, Tier 2 Secondary, Tier 3 Backup)
        contacts = get_contacts(cls.user_id)
        if len(contacts) < 3:
            cls.contact1_id = add_contact(cls.user_id, "Tier 1 Guardian", "9876543210", priority=1)
            cls.contact2_id = add_contact(cls.user_id, "Tier 2 Neighbor", "9876543211", priority=2)
            cls.contact3_id = add_contact(cls.user_id, "Tier 3 Colleague", "9876543212", priority=3)
        else:
            cls.contact1_id = contacts[0]["id"]
            cls.contact2_id = contacts[1]["id"]
            cls.contact3_id = contacts[2]["id"]

    def setUp(self):
        """Reset rate limiter before each test."""
        rate_limiter.clear_all()

    def test_01_trigger_sos_fall_detection(self):
        """POST /api/sos should accept 'fall_detection' trigger and record initial breadcrumb."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        payload = {
            "trigger_type": "fall_detection",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy": 8.5,
            "speed": 0.0
        }
        res = self.client.post("/api/sos", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["event"]["trigger_type"], "fall_detection")
        self.assertIn("tracking_url", data)

        event_id = data.get("event_id") or data["event"]["id"]
        # Verify initial breadcrumb was recorded
        crumbs = get_breadcrumbs(event_id)
        self.assertGreaterEqual(len(crumbs), 1)
        self.assertAlmostEqual(crumbs[0]["latitude"], 12.9716)
        self.assertAlmostEqual(crumbs[0]["longitude"], 77.5946)

    def test_02_continuous_live_location_breadcrumbs(self):
        """POST /api/sos/<id>/location should append coordinate breadcrumbs and update event."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        # 1. Create base event
        res_sos = self.client.post("/api/sos", json={
            "trigger_type": "manual",
            "latitude": 12.9710,
            "longitude": 77.5940
        })
        event_id = res_sos.get_json().get("event_id") or res_sos.get_json()["event"]["id"]

        # 2. Stream coordinate update #1
        res1 = self.client.post(f"/api/sos/{event_id}/location", json={
            "latitude": 12.9725,
            "longitude": 77.5955,
            "accuracy": 5.0,
            "speed": 1.2
        })
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertIn("https://www.google.com/maps?q=12.9725,77.5955", data1["maps_url"])

        # 3. Stream coordinate update #2
        res2 = self.client.post(f"/api/sos/{event_id}/location", json={
            "latitude": 12.9740,
            "longitude": 77.5970,
            "accuracy": 4.2,
            "speed": 1.5
        })
        self.assertEqual(res2.status_code, 200)

        # 4. Verify breadcrumb trail in SQLite
        crumbs = get_breadcrumbs(event_id)
        self.assertGreaterEqual(len(crumbs), 3) # Initial + 2 updates

        # 5. Verify latest location on event is updated to newest point
        updated_event = get_sos_event_by_id(event_id)
        self.assertAlmostEqual(updated_event["latitude"], 12.9740)
        self.assertAlmostEqual(updated_event["longitude"], 77.5970)

    def test_03_get_sos_tracking_endpoint(self):
        """GET /api/sos/<id>/tracking should return live tracking telemetry and breadcrumbs."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        res_sos = self.client.post("/api/sos", json={
            "trigger_type": "hand_gesture",
            "latitude": 13.0827,
            "longitude": 80.2707
        })
        event_id = res_sos.get_json().get("event_id") or res_sos.get_json()["event"]["id"]

        res = self.client.get(f"/api/sos/{event_id}/tracking")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["event_id"], event_id)
        self.assertEqual(data["user_name"], "Phase 6 Tester")
        self.assertEqual(data["trigger_type"], "hand_gesture")
        self.assertIn("latest_location", data)
        self.assertAlmostEqual(data["latest_location"]["latitude"], 13.0827)
        self.assertIsInstance(data["breadcrumbs"], list)

    def test_04_emergency_acknowledgement(self):
        """POST /api/sos/<id>/acknowledge should mark event as acknowledged and record responder."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        res_sos = self.client.post("/api/sos", json={"trigger_type": "manual"})
        event_id = res_sos.get_json().get("event_id") or res_sos.get_json()["event"]["id"]

        res_ack = self.client.post(f"/api/sos/{event_id}/acknowledge", json={
            "acknowledged_by": "Paramedic Unit 4"
        })
        self.assertEqual(res_ack.status_code, 200)
        data = res_ack.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Paramedic Unit 4", data["message"])
        self.assertEqual(data["event"]["status"], "acknowledged")
        self.assertEqual(data["event"]["acknowledged_by"], "Paramedic Unit 4")
        self.assertIsNotNone(data["event"]["acknowledged_at"])

    def test_05_emergency_escalation_protocol(self):
        """POST /api/sos/<id>/escalate should increment tier level and dispatch escalation alerts."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        res_sos = self.client.post("/api/sos", json={
            "trigger_type": "voice",
            "latitude": 12.9716,
            "longitude": 77.5946
        })
        event_id = res_sos.get_json().get("event_id") or res_sos.get_json()["event"]["id"]

        # Escalate unacknowledged alert
        res_esc = self.client.post(f"/api/sos/{event_id}/escalate")
        self.assertEqual(res_esc.status_code, 200)
        data = res_esc.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["escalation_level"], 2)

        # Verify escalation dispatches are logged to notification_logs
        logs = get_notification_logs(event_id)
        esc_logs = [l for l in logs if "escalation" in l["channel"]]
        self.assertGreater(len(esc_logs), 0)

        # Acknowledge the event
        self.client.post(f"/api/sos/{event_id}/acknowledge", json={"acknowledged_by": "Neighbor"})

        # Subsequent escalation on an acknowledged event must be rejected
        res_esc_blocked = self.client.post(f"/api/sos/{event_id}/escalate")
        self.assertEqual(res_esc_blocked.status_code, 400)
        self.assertIn("already been acknowledged", res_esc_blocked.get_json()["message"])

    def test_06_safety_checkin_lifecycle(self):
        """Safety check-in timer should start, report status, and complete successfully."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        # 1. Start check-in timer (15 minutes)
        res_start = self.client.post("/api/safety-checkin/start", json={
            "duration_minutes": 15,
            "note": "Walking to subway station alone"
        })
        self.assertEqual(res_start.status_code, 201)
        checkin_data = res_start.get_json()["checkin"]
        self.assertEqual(checkin_data["duration_minutes"], 15)
        self.assertEqual(checkin_data["status"], "active")

        # 2. Query status
        res_status = self.client.get("/api/safety-checkin/status")
        self.assertEqual(res_status.status_code, 200)
        st = res_status.get_json()
        self.assertTrue(st["active"])
        self.assertGreater(st["remaining_seconds"], 0)
        self.assertEqual(st["checkin"]["note"], "Walking to subway station alone")

        # 3. Confirm check-in (user is safe)
        res_checkin = self.client.post("/api/safety-checkin/checkin")
        self.assertEqual(res_checkin.status_code, 200)
        self.assertTrue(res_checkin.get_json()["success"])

        # 4. Verify no active checkin remains
        res_status2 = self.client.get("/api/safety-checkin/status")
        self.assertFalse(res_status2.get_json()["active"])

    def test_07_safety_checkin_expired_emergency_trigger(self):
        """Expired safety check-in should trigger automated multi-channel emergency alert."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        # Start check-in with note
        self.client.post("/api/safety-checkin/start", json={
            "duration_minutes": 5,
            "note": "Late night jog in dark park"
        })

        # Simulate expiration trigger
        res_exp = self.client.post("/api/safety-checkin/trigger-expired", json={
            "latitude": 12.9716,
            "longitude": 77.5946
        })
        self.assertEqual(res_exp.status_code, 200)
        data = res_exp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("emergency alert triggered", data["message"].lower())

        event_id = data["event_id"]
        event = get_sos_event_by_id(event_id)
        self.assertEqual(event["trigger_type"], "safety_checkin")

        # Checkin record must be marked 'expired_triggered'
        active_check = get_active_safety_checkin(self.user_id)
        self.assertIsNone(active_check)

    def test_08_contact_priority_tiers(self):
        """get_contacts_by_priority should accurately filter by priority tiers."""
        t1 = get_contacts_by_priority(self.user_id, priority=1)
        self.assertTrue(all(c["priority"] == 1 for c in t1))

        t2 = get_contacts_by_priority(self.user_id, priority=2)
        self.assertTrue(all(c["priority"] == 2 for c in t2))

        t3 = get_contacts_by_priority(self.user_id, priority=3)
        self.assertTrue(all(c["priority"] == 3 for c in t3))

    def test_09_invalid_coordinates_and_nonexistent_events(self):
        """Location breadcrumbs endpoint should reject nonexistent events and invalid coordinates."""
        # Nonexistent event
        r1 = self.client.post("/api/sos/999999/location", json={"latitude": 12.0, "longitude": 77.0})
        self.assertEqual(r1.status_code, 404)

        # Valid event, out of bound coords
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
        res_sos = self.client.post("/api/sos", json={"trigger_type": "manual"})
        event_id = res_sos.get_json().get("event_id") or res_sos.get_json()["event"]["id"]

        r2 = self.client.post(f"/api/sos/{event_id}/location", json={"latitude": 120.0, "longitude": 77.0})
        self.assertEqual(r2.status_code, 400)

        r3 = self.client.post(f"/api/sos/{event_id}/location", json={"latitude": "invalid", "longitude": "coords"})
        self.assertEqual(r3.status_code, 400)

    def test_10_safety_checkin_validation(self):
        """Safety check-in should reject duration <= 0 or > 1440."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        r1 = self.client.post("/api/safety-checkin/start", json={"duration_minutes": 0})
        self.assertEqual(r1.status_code, 400)

        r2 = self.client.post("/api/safety-checkin/start", json={"duration_minutes": 2000})
        self.assertEqual(r2.status_code, 400)


if __name__ == "__main__":
    unittest.main()
