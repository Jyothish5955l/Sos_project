import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_dir)

from app import app
from database import get_connection, initialize_database, create_user, get_user_by_email
from rate_limiter import rate_limiter


class TestPhase2Backend(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.patcher = patch("urllib.request.urlopen")
        cls.mock_urlopen = cls.patcher.start()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
        mock_resp.__enter__.return_value = mock_resp
        cls.mock_urlopen.return_value = mock_resp

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        rate_limiter.clear_all()
        self.client = app.test_client()
        # Ensure a test user exists
        user = get_user_by_email("test_phase2@sosguardian.local")
        if not user:
            self.user_id = create_user(
                "Phase 2 Tester",
                "test_phase2@sosguardian.local",
                "pbkdf2:sha256:dummyhash"
            )
        else:
            self.user_id = user["id"]

        # Clean old contacts from previous test runs to prevent accumulation
        conn = get_connection()
        conn.execute("DELETE FROM notification_logs WHERE contact_id IN (SELECT id FROM emergency_contacts WHERE user_id = ?)", (self.user_id,))
        conn.execute("DELETE FROM emergency_contacts WHERE user_id = ?", (self.user_id,))
        conn.commit()
        conn.close()

    def test_01_health_endpoint(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('status'), 'healthy')

    def test_02_gesture_endpoint_decoupled(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
        res = self.client.post('/api/gesture/detect')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('client_side_required'))

    def test_03_add_and_get_contact_with_telegram(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        # Add contact with telegram_chat_id
        res = self.client.post('/api/contacts', json={
            "name": "Mom Telegram",
            "phone": "+1234567890",
            "telegram_chat_id": "@mom_emergency"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        contact = data.get('contact')
        self.assertEqual(contact.get('telegram_chat_id'), '@mom_emergency')
        contact_id = contact.get('id')

        # Verify get_contacts returns telegram_chat_id
        res_get = self.client.get('/api/contacts')
        self.assertEqual(res_get.status_code, 200)
        contacts = res_get.get_json().get('contacts', [])
        found = [c for c in contacts if c.get('id') == contact_id]
        self.assertTrue(len(found) > 0)
        self.assertEqual(found[0].get('telegram_chat_id'), '@mom_emergency')

    def test_04_sos_with_gps(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        res = self.client.post('/api/sos', json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "trigger_type": "manual"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        event = data.get('event')
        self.assertEqual(event.get('latitude'), 12.9716)
        self.assertEqual(event.get('longitude'), 77.5946)
        self.assertTrue(event.get('location_available'))
        self.assertIn("https://www.google.com/maps?q=", event.get('maps_url'))

    def test_05_sos_without_gps_resilience(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        # Missing latitude and longitude
        res = self.client.post('/api/sos', json={
            "trigger_type": "hand_gesture"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        event = data.get('event')
        self.assertIsNone(event.get('latitude'))
        self.assertIsNone(event.get('longitude'))
        self.assertIsNone(event.get('maps_url'))
        self.assertFalse(event.get('location_available'))
        self.assertEqual(event.get('trigger_type'), 'hand_gesture')

    def test_06_sos_invalid_coordinates_fallback(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        # Invalid out-of-bounds coordinates
        res = self.client.post('/api/sos', json={
            "latitude": 999.0,
            "longitude": -999.0,
            "trigger_type": "voice"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        event = data.get('event')
        self.assertIsNone(event.get('latitude'))
        self.assertFalse(event.get('location_available'))
        self.assertEqual(event.get('trigger_type'), 'voice')

    def test_07_sos_history_contains_both_modes(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

        res = self.client.get('/api/sos/history')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        events = data.get('events', [])
        self.assertTrue(len(events) >= 2)


if __name__ == '__main__':
    unittest.main()
