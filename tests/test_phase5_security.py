"""
SOS Guardian - Phase 5 Security Hardening & Isolation Test Suite
Verifies security headers, session hygiene, sliding-window rate limiting,
input validation, cross-user data isolation, and route authorization.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

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
    create_sos_event
)
from rate_limiter import rate_limiter


class TestPhase5Security(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.patcher = patch("urllib.request.urlopen")
        cls.mock_urlopen = cls.patcher.start()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
        mock_resp.__enter__.return_value = mock_resp
        cls.mock_urlopen.return_value = mock_resp

        cls.client = app.test_client()
        app.config["TESTING"] = True

        # Clear rate limiter before running test suite
        rate_limiter.clear_all()

        # Create two distinct test users to verify cross-user isolation
        cls.email_user_a = "security_user_a@sosguardian.local"
        cls.email_user_b = "security_user_b@sosguardian.local"

        u_a = get_user_by_email(cls.email_user_a)
        if not u_a:
            cls.user_a_id = create_user("Security User A", cls.email_user_a, "valid_hash_a")
        else:
            cls.user_a_id = u_a["id"]

        u_b = get_user_by_email(cls.email_user_b)
        if not u_b:
            cls.user_b_id = create_user("Security User B", cls.email_user_b, "valid_hash_b")
        else:
            cls.user_b_id = u_b["id"]

        # Add a contact specifically owned by User A
        cls.contact_a_id = add_contact(
            cls.user_a_id,
            "User A Trusted Contact",
            "+15551112222",
            telegram_chat_id="@user_a_contact"
        )

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        # Clear rate limits before individual tests to ensure isolation
        rate_limiter.clear_all()

    def test_01_security_headers_present(self):
        """Responses must include X-Content-Type-Options, X-Frame-Options, and X-XSS-Protection."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        headers = response.headers
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("camera=(self)", headers.get("Permissions-Policy", ""))

    def test_02_session_cookie_hygiene(self):
        """Session cookies must be HttpOnly and SameSite=Lax."""
        cookie_httponly = app.config.get("SESSION_COOKIE_HTTPONLY")
        cookie_samesite = app.config.get("SESSION_COOKIE_SAMESITE")

        self.assertTrue(cookie_httponly, "Session cookie must have HttpOnly set to True")
        self.assertEqual(cookie_samesite, "Lax", "Session cookie SameSite must be Lax")

    def test_03_login_rate_limiting(self):
        """Failed login attempts beyond threshold must be blocked with HTTP 429 and Retry-After."""
        payload = {
            "email": "brute_force_target@sosguardian.local",
            "password": "wrong_password"
        }

        # First 5 attempts should return 401 (invalid credentials)
        for i in range(5):
            res = self.client.post("/api/auth/login", json=payload)
            self.assertEqual(res.status_code, 401, f"Attempt #{i+1} should return 401")

        # 6th attempt should be blocked by rate limiter with 429
        blocked_res = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(blocked_res.status_code, 429)

        data = blocked_res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Rate limit exceeded", data["message"])
        self.assertIn("Retry-After", blocked_res.headers)

    def test_04_sos_rate_limiting(self):
        """Rapid successive SOS triggers within 3 seconds must be throttled with HTTP 429."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        payload = {"trigger_type": "manual"}

        # 1st request should succeed
        res1 = self.client.post("/api/sos", json=payload)
        self.assertEqual(res1.status_code, 200)

        # 2nd immediate request within 3 seconds should be throttled
        res2 = self.client.post("/api/sos", json=payload)
        self.assertEqual(res2.status_code, 429)
        self.assertIn("Rate limit exceeded", res2.get_json()["message"])

    def test_05_test_contact_rate_limiting(self):
        """Test contact endpoint must throttle after 5 requests per minute."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        # 5 allowed attempts
        for i in range(5):
            res = self.client.post(f"/api/contacts/{self.contact_a_id}/test")
            self.assertEqual(res.status_code, 200)

        # 6th request throttled
        throttled = self.client.post(f"/api/contacts/{self.contact_a_id}/test")
        self.assertEqual(throttled.status_code, 429)

    def test_06_register_input_validation(self):
        """Registration must reject invalid email, short password, long password, or empty name."""
        # 1. Empty name
        r1 = self.client.post("/api/auth/register", json={"name": "", "email": "test@test.com", "password": "password123"})
        self.assertEqual(r1.status_code, 400)

        # 2. Invalid email format
        r2 = self.client.post("/api/auth/register", json={"name": "Alice", "email": "not-an-email", "password": "password123"})
        self.assertEqual(r2.status_code, 400)
        self.assertIn("valid email", r2.get_json()["message"])

        # 3. Short password
        r3 = self.client.post("/api/auth/register", json={"name": "Alice", "email": "alice@test.com", "password": "123"})
        self.assertEqual(r3.status_code, 400)
        self.assertIn("at least 6 characters", r3.get_json()["message"])

        # 4. Oversized password (>128 chars)
        r4 = self.client.post("/api/auth/register", json={"name": "Alice", "email": "alice@test.com", "password": "A" * 150})
        self.assertEqual(r4.status_code, 400)
        self.assertIn("cannot exceed 128 characters", r4.get_json()["message"])

    def test_07_contact_input_validation(self):
        """Contact creation must validate phone number format, name length, and telegram username."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        # 1. Invalid phone format
        r1 = self.client.post("/api/contacts", json={"name": "Bob", "phone": "invalid-phone"})
        self.assertEqual(r1.status_code, 400)
        self.assertIn("valid phone number", r1.get_json()["message"])

        # 2. Invalid Telegram format
        r2 = self.client.post("/api/contacts", json={"name": "Bob", "phone": "+15551234567", "telegram_chat_id": "invalid space id"})
        self.assertEqual(r2.status_code, 400)
        self.assertIn("valid Telegram", r2.get_json()["message"])

    def test_08_sos_trigger_type_validation(self):
        """SOS endpoint must reject unauthorized or invalid trigger types."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        # Invalid trigger type
        res = self.client.post("/api/sos", json={"trigger_type": "arbitrary_exploit"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid trigger_type", res.get_json()["message"])

    def test_09_cross_user_contact_isolation(self):
        """User B must NOT be able to view, test, or delete User A's contacts."""
        # Authenticate as User B
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_b_id

        # 1. User B viewing contacts must not see User A's contact
        list_res = self.client.get("/api/contacts")
        self.assertEqual(list_res.status_code, 200)
        b_contact_ids = [c["id"] for c in list_res.get_json()["contacts"]]
        self.assertNotIn(self.contact_a_id, b_contact_ids)

        # 2. User B testing User A's contact must return 404 Not Found
        test_res = self.client.post(f"/api/contacts/{self.contact_a_id}/test")
        self.assertEqual(test_res.status_code, 404)

        # 3. User B attempting to delete User A's contact must return 404 Not Found
        del_res = self.client.delete(f"/api/contacts/{self.contact_a_id}/test")
        # Route is DELETE /api/contacts/<id>
        del_res = self.client.delete(f"/api/contacts/{self.contact_a_id}")
        self.assertEqual(del_res.status_code, 404)

    def test_10_unauthenticated_route_protection(self):
        """Unauthenticated requests to protected endpoints must be rejected with HTTP 401."""
        unauthed_client = app.test_client()

        endpoints = [
            ("GET", "/api/contacts"),
            ("POST", "/api/contacts"),
            ("DELETE", "/api/contacts/1"),
            ("POST", "/api/contacts/1/test"),
            ("POST", "/api/sos"),
            ("GET", "/api/sos/history"),
            ("GET", "/api/auth/me"),
        ]

        for method, path in endpoints:
            if method == "GET":
                res = unauthed_client.get(path)
            elif method == "POST":
                res = unauthed_client.post(path)
            elif method == "DELETE":
                res = unauthed_client.delete(path)

            self.assertEqual(
                res.status_code,
                401,
                f"Endpoint {method} {path} should be protected with 401"
            )


if __name__ == "__main__":
    unittest.main()

