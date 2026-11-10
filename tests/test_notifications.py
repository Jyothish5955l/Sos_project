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
    HttpSMSProvider,
    get_sms_provider,
    format_emergency_sms,
    format_test_sms
)
from notifications import NotificationService, notification_service, send_httpsms_alert
from rate_limiter import rate_limiter


class TestNotificationDelivery(unittest.TestCase):

    def setUp(self):
        """Clear sliding window rate limits before every test run."""
        rate_limiter.clear_all()

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

    def test_07b_fast2sms_clean_phone_number(self):
        """Fast2SMSProvider.clean_phone_number should normalize Indian mobile numbers to 10 digits."""
        self.assertEqual(Fast2SMSProvider.clean_phone_number("+91 9876543210"), "9876543210")
        self.assertEqual(Fast2SMSProvider.clean_phone_number("+919876543210"), "9876543210")
        self.assertEqual(Fast2SMSProvider.clean_phone_number("09876543210"), "9876543210")
        self.assertEqual(Fast2SMSProvider.clean_phone_number("98765-43210"), "9876543210")
        self.assertEqual(Fast2SMSProvider.clean_phone_number("9876543210"), "9876543210")

    @patch("urllib.request.urlopen")
    def test_07c_fast2sms_success(self, mock_urlopen):
        """Fast2SMSProvider should dispatch POST with route='q' and authorization header."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "return": True,
            "request_id": "fast2sms_req_998877",
            "message": ["SMS sent successfully."]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = Fast2SMSProvider(api_key="fast2sms_test_secret_key")
        self.assertTrue(provider.is_configured())

        res = provider.send_sms("+91 9876543210", "🚨 Emergency Fast2SMS alert")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "sent")
        self.assertEqual(res["phone"], "9876543210")
        self.assertEqual(res["request_id"], "fast2sms_req_998877")

        # Verify the request payload sent to Fast2SMS dev/bulkV2
        self.assertEqual(mock_urlopen.call_count, 1)
        req_sent = mock_urlopen.call_args[0][0]
        self.assertEqual(req_sent.full_url, "https://www.fast2sms.com/dev/bulkV2")
        self.assertEqual(req_sent.headers.get("Authorization"), "fast2sms_test_secret_key")
        payload = json.loads(req_sent.data.decode("utf-8"))
        self.assertEqual(payload.get("route"), "q")
        self.assertEqual(payload.get("numbers"), "9876543210")

    def test_07d_format_emergency_sms_maps_url_and_fallback(self):
        """format_emergency_sms should include clickable Google Maps pin or explicit 'GPS Unavailable'."""
        # 1. With coordinates
        sms_with_coords = format_emergency_sms(
            user_name="Jane Doe",
            trigger_type="manual",
            latitude=12.9716,
            longitude=77.5946
        )
        self.assertIn("https://www.google.com/maps?q=12.9716,77.5946", sms_with_coords)
        self.assertIn("Jane Doe", sms_with_coords)
        self.assertIn("manual", sms_with_coords)

        # 2. Without coordinates (fallback)
        sms_no_coords = format_emergency_sms(
            user_name="Jane Doe",
            trigger_type="voice",
            latitude=None,
            longitude=None
        )
        self.assertIn("GPS Unavailable", sms_no_coords)
        self.assertNotIn("https://www.google.com/maps", sms_no_coords)

    def test_07e_httpsms_format_e164(self):
        """HttpSMSProvider.format_e164 should normalize numbers to standard E.164 (+91 for Indian numbers)."""
        self.assertEqual(HttpSMSProvider.format_e164("9876543210"), "+919876543210")
        self.assertEqual(HttpSMSProvider.format_e164("09876543210"), "+919876543210")
        self.assertEqual(HttpSMSProvider.format_e164("919876543210"), "+919876543210")
        self.assertEqual(HttpSMSProvider.format_e164("+91 98765-43210"), "+919876543210")
        self.assertEqual(HttpSMSProvider.format_e164("+15551234567"), "+15551234567")

    def test_07f_httpsms_unconfigured_fallback(self):
        """send_httpsms_alert should safely fallback to mock simulation when credentials are missing."""
        with patch.dict(os.environ, {"HTTPSMS_API_KEY": "", "HTTPSMS_FROM_NUMBER": ""}):
            res = send_httpsms_alert("9876543210", "🚨 Distress Test Alert")
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "simulated")
            self.assertEqual(res["provider"], "mock")
            self.assertEqual(res["phone"], "+919876543210")

    @patch("urllib.request.urlopen")
    def test_07g_httpsms_live_dispatch_success(self, mock_urlopen):
        """send_httpsms_alert should dispatch POST to httpSMS API with headers and E.164 payload."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "data": {
                "id": "msg_httpsms_12345",
                "content": "🚨 SOS EMERGENCY ALERT!",
                "from": "+918888888888",
                "to": "+919876543210"
            }
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch.dict(os.environ, {
            "SMS_PROVIDER": "httpsms",
            "HTTPSMS_API_KEY": "test_httpsms_api_key_secret",
            "HTTPSMS_FROM_NUMBER": "+918888888888"
        }):
            res = send_httpsms_alert("9876543210", "🚨 SOS EMERGENCY ALERT!")
            self.assertTrue(res["success"])
            self.assertEqual(res["status"], "sent")
            self.assertEqual(res["provider"], "httpsms")
            self.assertEqual(res["phone"], "+919876543210")
            self.assertEqual(res["message_id"], "msg_httpsms_12345")

            # Verify request
            self.assertEqual(mock_urlopen.call_count, 1)
            req_sent = mock_urlopen.call_args[0][0]
            self.assertEqual(req_sent.full_url, "https://api.httpsms.com/v1/messages/send")
            self.assertEqual(req_sent.headers.get("X-api-key"), "test_httpsms_api_key_secret")
            self.assertEqual(req_sent.headers.get("Content-type"), "application/json")
            self.assertEqual(req_sent.headers.get("Accept"), "application/json")

            sent_payload = json.loads(req_sent.data.decode("utf-8"))
            self.assertEqual(sent_payload.get("to"), "+919876543210")
            self.assertEqual(sent_payload.get("from"), "+918888888888")
            self.assertEqual(sent_payload.get("content"), "🚨 SOS EMERGENCY ALERT!")

    @patch("urllib.request.urlopen")
    def test_07h_httpsms_http_error_graceful_handling(self, mock_urlopen):
        """send_httpsms_alert should handle HTTPError gracefully without throwing exceptions."""
        error_body = json.dumps({
            "message": "Invalid API Key or unauthorized phone number"
        }).encode("utf-8")

        mock_http_error = urllib.error.HTTPError(
            url="https://api.httpsms.com/v1/messages/send",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body))
        )
        mock_urlopen.side_effect = mock_http_error

        with patch.dict(os.environ, {
            "SMS_PROVIDER": "httpsms",
            "HTTPSMS_API_KEY": "bad_key",
            "HTTPSMS_FROM_NUMBER": "+918888888888"
        }):
            res = send_httpsms_alert("9876543210", "🚨 Alert")
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "failed")
            self.assertEqual(res["provider"], "httpsms")
            self.assertIn("Invalid API Key", res["error"])
            self.assertEqual(res["http_code"], 401)

    @patch("urllib.request.urlopen")
    def test_07i_httpsms_multiple_phone_numbers(self, mock_urlopen):
        """send_httpsms_alert should accept list of phone numbers and return list of dispatch results."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"id": "msg_batch_1"}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch.dict(os.environ, {
            "SMS_PROVIDER": "httpsms",
            "HTTPSMS_API_KEY": "test_key",
            "HTTPSMS_FROM_NUMBER": "+918888888888"
        }):
            results = send_httpsms_alert(["9876543210", "9876543211"], "🚨 Batch Alert")
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["phone"], "+919876543210")
            self.assertEqual(results[1]["phone"], "+919876543211")
            self.assertEqual(mock_urlopen.call_count, 2)

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

    def test_12_end_to_end_contact_creation_and_sos_dispatch(self):
        """
        End-to-End Test:
        1. User adds a guardian contact with a 10-digit mobile number via POST /api/contacts.
        2. Recipient requires NO app or registration; saved directly to SQLite.
        3. User triggers emergency via POST /api/sos.
        4. Emergency service pulls saved numbers from SQLite and dispatches SMS with Google Maps pin.
        5. Delivery is audited in notification_logs table.
        """
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        # 1. Add guardian contact with 10-digit mobile number
        contact_payload = {
            "name": "Guardian Hero",
            "phone": "9876543210",
            "telegram_chat_id": None
        }
        res_add = self.client.post("/api/contacts", json=contact_payload)
        self.assertIn(res_add.status_code, [200, 201])
        guardian_id = res_add.get_json().get("contact_id") or res_add.get_json()["contact"]["id"]

        # Verify saved in SQLite
        db_contacts = get_contacts(self.user_id)
        saved_guardian = next((c for c in db_contacts if c["id"] == guardian_id), None)
        self.assertIsNotNone(saved_guardian)
        self.assertEqual(saved_guardian["phone"], "9876543210")
        self.assertEqual(saved_guardian["name"], "Guardian Hero")

        # 2. Trigger SOS distress signal with location
        sos_payload = {
            "trigger_type": "manual",
            "latitude": 13.0827,
            "longitude": 80.2707
        }
        res_sos = self.client.post("/api/sos", json=sos_payload)
        self.assertEqual(res_sos.status_code, 200)
        sos_data = res_sos.get_json()
        self.assertTrue(sos_data["success"])
        sos_event_id = sos_data.get("event_id") or sos_data["event"]["id"]

        # 3. Verify notification_logs in SQLite recorded an SMS delivery to the guardian
        logs = get_notification_logs(sos_event_id)
        guardian_sms_logs = [
            l for l in logs
            if l["contact_id"] == guardian_id and l["channel"] == "sms"
        ]
        self.assertEqual(len(guardian_sms_logs), 1)
        log_entry = guardian_sms_logs[0]
        self.assertEqual(log_entry["recipient"], "9876543210")
        self.assertIn(log_entry["status"], ["sent", "simulated"])


if __name__ == "__main__":
    unittest.main()
