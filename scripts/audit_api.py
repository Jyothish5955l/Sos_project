import sys
import os
from unittest.mock import MagicMock

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_dir)

# Mock cv2, mediapipe, and numpy so we can test the Flask app routes
sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['numpy'] = MagicMock()

try:
    from app import app
    print("Flask app loaded with mocked cv2/mediapipe.")
except Exception as e:
    print(f"FAILED to load Flask app: {e}")
    sys.exit(1)

client = app.test_client()

print("\n--- 1. Testing GET /api/health ---")
res = client.get('/api/health')
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 2. Testing GET /api/auth/me (unauthenticated) ---")
res = client.get('/api/auth/me')
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 3. Testing POST /api/auth/login (missing params) ---")
res = client.post('/api/auth/login', json={})
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 4. Testing POST /api/sos (unauthenticated) ---")
res = client.post('/api/sos', json={"latitude": 12.9716, "longitude": 77.5946})
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 5. Testing POST /api/sos without coordinates (authenticated session) ---")
with client.session_transaction() as sess:
    sess['user_id'] = 1
res = client.post('/api/sos', json={"trigger_type": "button"})
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 6. Testing POST /api/sos with coordinates (authenticated session) ---")
res = client.post('/api/sos', json={"latitude": 12.9716, "longitude": 77.5946, "trigger_type": "button"})
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 7. Testing GET /api/contacts (authenticated session) ---")
res = client.get('/api/contacts')
print(f"Status: {res.status_code}, Body: {res.get_json()}")

print("\n--- 8. Testing GET /api/sos/history (authenticated session) ---")
res = client.get('/api/sos/history')
print(f"Status: {res.status_code}, Body: {res.get_json()}")
