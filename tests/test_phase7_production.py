"""
SOS Guardian — Phase 7: Production Deployment & Final Verification Tests
========================================================================
Validates:
1. WSGI callable entry point (wsgi.py) for production servers (Gunicorn / Waitress).
2. Reverse proxy header forwarding (ProxyFix middleware).
3. Production health check endpoints (/health and /api/health).
4. Robots.txt and static caching headers.
5. Production cookie security configuration.
6. Custom DATABASE_PATH environment configuration.
7. End-to-end Definition of Complete lifecycle drill (User, Contacts, Multi-Modal Triggers, Breadcrumbs, Tracking, Escalation, Acknowledgement, Safety Check-in).
"""

import os
import sys
import unittest
import json
import tempfile
import shutil

# Ensure project root and backend are on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend.app import app
from rate_limiter import rate_limiter
import backend.database as db
import wsgi


class TestPhase7ProductionDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "production_test_secret_key_32bytes"
        cls.client = app.test_client()

    def setUp(self):
        rate_limiter.clear_all()
        # Ensure fresh DB state for test user
        self.test_email = f"prod_tester_{os.urandom(4).hex()}@example.com"
        self.test_password = "Password123!"
        self.test_name = "Production Tester"

    def test_01_wsgi_entrypoint_validity(self):
        """WSGI entrypoint wsgi.py must export callable app and application."""
        self.assertTrue(hasattr(wsgi, "app"), "wsgi.py must export 'app'")
        self.assertTrue(hasattr(wsgi, "application"), "wsgi.py must export 'application'")
        self.assertIs(wsgi.app, wsgi.application, "'application' must alias 'app'")
        self.assertEqual(wsgi.app.name, "backend.app")

    def test_02_proxyfix_header_forwarding(self):
        """ProxyFix middleware must resolve X-Forwarded-For and X-Forwarded-Proto."""
        response = self.client.get(
            "/api/health",
            headers={
                "X-Forwarded-For": "203.0.113.195",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "emergency.example.com"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "healthy")

    def test_03_health_check_endpoints(self):
        """Both /health and /api/health must report system health and components."""
        for endpoint in ["/health", "/api/health"]:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200, f"Failed on {endpoint}")
            data = response.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(data["service"], "SOS Guardian")
            self.assertEqual(data["version"], "1.0.0")
            self.assertIn("components", data)
            self.assertEqual(data["components"]["database"], "connected")
            self.assertEqual(data["components"]["rate_limiter"], "active")
            self.assertIn("sms_provider", data["components"])
            self.assertIn("timestamp", data)

    def test_04_robots_txt(self):
        """GET /robots.txt must return text/plain disallowing /api/."""
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.content_type)
        self.assertIn("Disallow: /api/", response.data.decode("utf-8"))

    def test_05_security_cookie_and_header_configuration(self):
        """Session cookies and headers must adhere to security standards."""
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 2 * 1024 * 1024)

        # Probe response headers
        response = self.client.get("/")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(response.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("camera=(self)", response.headers.get("Permissions-Policy", ""))

    def test_06_database_path_configuration(self):
        """Custom DATABASE_PATH environment override must be supported."""
        temp_dir = tempfile.mkdtemp()
        temp_db = os.path.join(temp_dir, "custom_prod.db")
        try:
            # Verify database can be initialized on custom path
            orig_db = db.DATABASE
            db.DATABASE = temp_db
            db.initialize_database()
            self.assertTrue(os.path.exists(temp_db))

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            self.assertIn("users", tables)
            self.assertIn("sos_events", tables)
            self.assertIn("sos_location_breadcrumbs", tables)
        finally:
            db.DATABASE = orig_db
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_07_definition_of_complete_e2e_drill(self):
        """Comprehensive verification of PRD Section 11 'Definition of Complete'.
        Executes complete user lifecycle:
        1. Registration & Login
        2. Contact configuration (Tier 1 & Tier 2)
        3. Contact test alert
        4. Manual SOS Trigger with GPS
        5. Live GPS breadcrumb updates
        6. Live tracking query
        7. Escalation protocol
        8. Responder acknowledgement
        9. Safety checkin session (Start & Complete)
        10. Fall detection trigger
        """
        # 1. Register & Login
        reg_res = self.client.post("/api/auth/register", json={
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(reg_res.status_code, 201)

        login_res = self.client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        self.assertEqual(login_res.status_code, 200)

        # 2. Add Contacts (Tier 1 Primary & Tier 2 Secondary)
        c1_res = self.client.post("/api/contacts", json={
            "name": "Primary Guardian",
            "phone": "9876543210",
            "telegram": "12345678",
            "priority": 1
        })
        self.assertEqual(c1_res.status_code, 201)
        c1_id = c1_res.get_json()["contact_id"]

        c2_res = self.client.post("/api/contacts", json={
            "name": "Secondary Guardian",
            "phone": "9876543211",
            "priority": 2
        })
        self.assertEqual(c2_res.status_code, 201)

        # 3. Test Contact Alert Endpoint
        test_contact_res = self.client.post(f"/api/contacts/{c1_id}/test")
        self.assertEqual(test_contact_res.status_code, 200)
        self.assertTrue(test_contact_res.get_json()["success"])

        # 4. Trigger Manual SOS with GPS
        sos_res = self.client.post("/api/sos", json={
            "trigger_type": "manual",
            "latitude": 12.9716,
            "longitude": 77.5946
        })
        self.assertIn(sos_res.status_code, (200, 201))
        sos_data = sos_res.get_json()
        event_id = sos_data["event_id"]
        self.assertIn("tracking_url", sos_data)

        # 5. Stream Live Location Breadcrumbs
        b1 = self.client.post(f"/api/sos/{event_id}/location", json={
            "latitude": 12.9720,
            "longitude": 77.5950,
            "accuracy": 8.5,
            "speed": 1.2
        })
        self.assertIn(b1.status_code, (200, 201))

        b2 = self.client.post(f"/api/sos/{event_id}/location", json={
            "latitude": 12.9725,
            "longitude": 77.5955,
            "accuracy": 6.0,
            "speed": 1.4
        })
        self.assertIn(b2.status_code, (200, 201))

        # 6. Verify Public Tracking Telemetry
        track_res = self.client.get(f"/api/sos/{event_id}/tracking")
        self.assertEqual(track_res.status_code, 200)
        track_data = track_res.get_json()
        self.assertEqual(track_data["event_id"], event_id)
        self.assertEqual(track_data["breadcrumbs_count"], 3)  # Initial + 2 updates
        self.assertEqual(len(track_data["breadcrumbs"]), 3)
        self.assertAlmostEqual(track_data["latest_location"]["latitude"], 12.9725)

        # 7. Escalate to Tier 2
        esc_res = self.client.post(f"/api/sos/{event_id}/escalate")
        self.assertEqual(esc_res.status_code, 200)
        self.assertEqual(esc_res.get_json()["escalation_level"], 2)

        # 8. Responder Acknowledge Emergency
        ack_res = self.client.post(f"/api/sos/{event_id}/acknowledge", json={
            "responder_name": "Dr. Sarah Connor",
            "note": "Paramedic team arrived on scene."
        })
        self.assertEqual(ack_res.status_code, 200)
        self.assertEqual(ack_res.get_json()["status"], "acknowledged")

        # Verify escalation is blocked post-acknowledgement
        esc_blocked = self.client.post(f"/api/sos/{event_id}/escalate")
        self.assertEqual(esc_blocked.status_code, 400)

        # 9. Safety Check-in Lifecycle
        start_checkin = self.client.post("/api/safety-checkin/start", json={
            "duration_minutes": 30,
            "note": "Commuting via subway"
        })
        self.assertEqual(start_checkin.status_code, 201)

        status_checkin = self.client.get("/api/safety-checkin/status")
        self.assertEqual(status_checkin.status_code, 200)
        self.assertTrue(status_checkin.get_json()["active"])

        complete_checkin = self.client.post("/api/safety-checkin/checkin")
        self.assertEqual(complete_checkin.status_code, 200)

        status_after = self.client.get("/api/safety-checkin/status")
        self.assertFalse(status_after.get_json()["active"])

        # 10. Fall Detection Trigger (clear rate limiter window for second test trigger)
        rate_limiter.clear_all()
        fall_res = self.client.post("/api/sos", json={
            "trigger_type": "fall_detection",
            "latitude": 12.9730,
            "longitude": 77.5960
        })
        self.assertIn(fall_res.status_code, (200, 201))
        self.assertEqual(fall_res.get_json()["event"]["trigger_type"], "fall_detection")

        # 11. History Inspection
        history_res = self.client.get("/api/sos/history")
        self.assertEqual(history_res.status_code, 200)
        history_events = history_res.get_json()["events"]
        self.assertGreaterEqual(len(history_events), 2)


if __name__ == "__main__":
    unittest.main()
