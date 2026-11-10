import sys
import os
from unittest.mock import MagicMock

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_dir)

sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['numpy'] = MagicMock()

from app import app
from database import get_connection

client = app.test_client()

print("--- Testing Cross-User Data Isolation ---")

# Check users in DB
conn = get_connection()
c = conn.cursor()
c.execute("SELECT id, name, email FROM users")
users = c.fetchall()
print(f"Users in DB: {[dict(u) for u in users]}")

c.execute("SELECT id, user_id, name, phone FROM emergency_contacts")
contacts = c.fetchall()
print(f"Contacts in DB: {[dict(ct) for ct in contacts]}")
conn.close()

if len(users) >= 2:
    u1_id = users[0]['id']
    u2_id = users[1]['id']

    # User 1 tries to fetch contacts
    with client.session_transaction() as sess:
        sess['user_id'] = u1_id
    res1 = client.get('/api/contacts')
    u1_contacts = res1.get_json()['contacts']

    # User 2 tries to fetch contacts
    with client.session_transaction() as sess:
        sess['user_id'] = u2_id
    res2 = client.get('/api/contacts')
    u2_contacts = res2.get_json()['contacts']

    print(f"\nUser {u1_id} contacts count: {len(u1_contacts)}")
    print(f"User {u2_id} contacts count: {len(u2_contacts)}")

    # Check if User 2 can delete User 1's contact
    if u1_contacts:
        target_id = u1_contacts[0]['id']
        del_res = client.delete(f'/api/contacts/{target_id}')
        print(f"User {u2_id} attempting to delete User {u1_id}'s contact (id={target_id}): Status {del_res.status_code}, Body: {del_res.get_json()}")
