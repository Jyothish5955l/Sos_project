"""
SOS Guardian - Multi-Channel Emergency Notification Test Suite
Phase 4 Automated Verification
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

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
    create_sos_event,
    get_sos_events,
    get_notification_logs,
    log_notification,
    update_sos_event_status
)
from providers.telegram_provider import TelegramProvider, telegram_provider
from providers.sms_provider import (
    MockSMSProvider,
    TwilioSMSProvider,
    Fast2SMSProvider,
    get_sms_provider,
    format_emergency_sms
)
from notifications import NotificationService, notification_service


class TestNotificationDelivery(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.client = app.test_client()
        app.config["TESTING"] = True

        # Ensure a clean test user exists
        cls.test_email = "phase4_tester@sosguardian.local"
        existing = get_user_by_email(cls.test_email)
        if not existing:
            cls.user_id = create_user(
                "Phase 4 Tester",
                cls.test_email,
                "hashed_password_123"
            )
        else:
            cls.user_id = existing["id"]

        # Ensure user has configured contacts (one with phone only, one with phone + telegram)
        contacts = get_contacts(cls.user_id)
        tg_contacts = [c for c in contacts if c.get("telegram_chat_id")]
        sms_contacts = [c for c in contacts if not c.get("telegram_chat_id")]

        if not sms_contacts:
            cls.contact1_id = add_contact(
                cls.user_id,
                "Emergency Contact SMS",
                "+15551234567",
                telegram_chat_id=None
            )
        else:
            cls.contact1_id = sms_contacts[0]["id"]

        if not tg_contacts:
            cls.contact2_id = add_contact(
                cls.user_id,
                "Emergency Contact Telegram",
                "+15559876543",
                telegram_chat_id="123456789"
            )
        else:
            cls.contact2_id = tg_contacts[0]["id"]

    def test_01_telegram_provider_unconfigured_simulated(self):
        """TelegramProvider without token should gracefully run in simulated mode without throwing."""
        provider = TelegramProvider(token="")
        self.assertFalse(provider.is_configured())

        res = provider.send_message("123456789", "🚨 SOS Test Alert")
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "telegram")
        self.assertEqual(res["status"], "simulated")
        self.assertEqual(res["chat_id"], "123456789")

    def test_02_telegram_provider_missing_chat_id(self):
        """TelegramProvider should safely reject empty or missing chat IDs."""
        provider = TelegramProvider(token="valid_looking_token_123")
        res = provider.send_message("", "🚨 Alert")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "failed")

    @patch("urllib.request.urlopen")
    def test_03_telegram_provider_live_dispatch_success(self, mock_urlopen):
        """TelegramProvider should correctly parse 200 OK from Telegram Bot API."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "ok": True,
            "result": {"message_id": 9876, "chat": {"id": 123456789}}
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = TelegramProvider(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        self.assertTrue(provider.is_configured())

        res = provider.send_message("123456789", "🚨 Emergency Alert")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "sent")
        self.assertEqual(res["message_id"], 9876)

    @patch("urllib.request.urlopen")
    def test_04_telegram_provider_400_chat_not_found(self, mock_urlopen):
        """TelegramProvider should parse 400 Bad Request and return a helpful error hint."""
        error_body = json.dumps({
            "ok": False,
            "error_code": 400,
            "description": "Bad Request: chat not found"
        }).encode("utf-8")

        mock_http_error = urllib.error.HTTPError(
            url="https://api.telegram.org/bot123/sendMessage",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body))
        )
        mock_urlopen.side_effect = mock_http_error

        provider = TelegramProvider(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        res = provider.send_message("999999999", "🚨 Alert")
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "failed")
        self.assertIn("start the bot first", res["error"])

    def test_05_sms_provider_mock(self):
        """MockSMSProvider should return simulated status and format messages properly."""
        provider = MockSMSProvider()
        res = provider.send_sms("+15553334444", "🚨 Test SMS")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "simulated")
        self.assertEqual(res["provider"], "mock")

    def test_06_sms_provider_factory(self):
        """get_sms_provider should safely fallback to mock when credentials are not configured."""
        with patch.dict(os.environ, {"SMS_PROVIDER": "twilio", "TWILIO_ACCOUNT_SID": ""}):
            provider = get_sms_provider()
            self.assertEqual(provider.name, "mock")

        with patch.dict(os.environ, {"SMS_PROVIDER": "mock"}):
            provider = get_sms_provider()
            self.assertEqual(provider.name, "mock")

    @patch("urllib.request.urlopen")
    def test_07_twilio_sms_success(self, mock_urlopen):
        """TwilioSMSProvider should dispatch POST with Basic Auth and return status sent."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "sid": "SM1234567890abcdef",
            "status": "queued"
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = TwilioSMSProvider(
            account_sid="AC1234567890abcdef",
            auth_token="auth_token_secret_123",
            from_number="+15550001111"
        )
        self.assertTrue(provider.is_configured())

        res = provider.send_sms("+15552223333", "🚨 Emergency SMS alert")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "sent")
        self.assertEqual(res["sid"], "SM1234567890abcdef")

    def test_08_multichannel_emergency_alerts_orchestration(self):
        """NotificationService should dispatch to both SMS and Telegram and persist logs in SQLite."""
        event_id = create_sos_event(
            user_id=self.user_id,
            latitude=12.9716,
            longitude=77.5946,
            maps_url="https://www.google.com/maps?q=12.9716,77.5946",
            trigger_type="voice",
            status="received"
        )

        contacts = [
            {"id": self.contact1_id, "name": "Primary SMS", "phone": "+15551112222", "telegram_chat_id": None},
            {"id": self.contact2_id, "name": "Secondary Telegram", "phone": "+15553334444", "telegram_chat_id": "456789"}
        ]

        report = notification_service.send_emergency_alerts(
            sos_event_id=event_id,
            user_name="Tester",
            trigger_type="voice",
            latitude=12.9716,
            longitude=77.5946,
            maps_url="https://www.google.com/maps?q=12.9716,77.5946",
            contacts=contacts
        )

        self.assertIn(report["overall_status"], ["simulated", "notification_sent"])
        self.assertEqual(report["total_contacts"], 2)

        # Verify persistent logs in database
        logs = get_notification_logs(event_id)
        self.assertGreaterEqual(len(logs), 3) # 2 SMS + 1 Telegram
        channels = [log["channel"] for log in logs]
        self.assertIn("sms", channels)
        self.assertIn("telegram", channels)

    def test_09_test_contact_notification_endpoint(self):
        """POST /api/contacts/<id>/test should test an individual contact's channels without full SOS."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        response = self.client.post(f"/api/contacts/{self.contact2_id}/test")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("results", data)
        self.assertIn("sms", data["results"])
        self.assertIn("telegram", data["results"])

    def test_10_test_contact_notification_unauthorized(self):
        """POST /api/contacts/<id>/test should enforce 401 when unauthenticated."""
        unauthed_client = app.test_client()
        response = unauthed_client.post(f"/api/contacts/{self.contact1_id}/test")
        self.assertEqual(response.status_code, 401)

    def test_11_history_endpoint_includes_notifications(self):
        """GET /api/sos/history should return SOS events with attached notifications array."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        response = self.client.get("/api/sos/history")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 0)

        # Check that events have notifications field
        first_event = data["events"][0]
        self.assertIn("notifications", first_event)
        self.assertIsInstance(first_event["notifications"], list)


if __name__ == "__main__":
    unittest.main()
