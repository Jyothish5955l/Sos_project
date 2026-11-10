import sqlite3
import os
from datetime import datetime, timedelta


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = os.path.join(
    BASE_DIR,
    "data",
    "sos_guardian.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    os.makedirs(
        os.path.dirname(DATABASE),
        exist_ok=True
    )

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password_hash TEXT NOT NULL,

            camera_permission INTEGER DEFAULT 0,

            microphone_permission INTEGER DEFAULT 0,

            location_permission INTEGER DEFAULT 0,

            protection_enabled INTEGER DEFAULT 0,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # --------------------------------------------------------
    # EMERGENCY CONTACTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_contacts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            name TEXT NOT NULL,

            phone TEXT NOT NULL,

            telegram_chat_id TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)


    # --------------------------------------------------------
    # SOS EVENTS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sos_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            latitude REAL,

            longitude REAL,

            maps_url TEXT,

            trigger_type TEXT NOT NULL,

            status TEXT NOT NULL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
    """)


    # --------------------------------------------------------
    # DEVICES
    # Kept temporarily for compatibility with old database.
    # Not used by the new website architecture.
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            device_token TEXT NOT NULL UNIQUE,

            device_name TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # --------------------------------------------------------
    # NOTIFICATION LOGS
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sos_event_id INTEGER,

            contact_id INTEGER,

            channel TEXT NOT NULL,

            recipient TEXT NOT NULL,

            status TEXT NOT NULL,

            provider TEXT,

            error_message TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (sos_event_id)
                REFERENCES sos_events(id),

            FOREIGN KEY (contact_id)
                REFERENCES emergency_contacts(id)
        )
    """)


    # --------------------------------------------------------
    # DATABASE MIGRATION
    # --------------------------------------------------------

    # Add columns if they do not exist
    cursor.execute("""
        PRAGMA table_info(emergency_contacts)
    """)

    contact_columns = [
        column["name"]
        for column in cursor.fetchall()
    ]

    if "user_id" not in contact_columns:

        cursor.execute("""
            ALTER TABLE emergency_contacts
            ADD COLUMN user_id INTEGER
        """)

    if "telegram_chat_id" not in contact_columns:

        cursor.execute("""
            ALTER TABLE emergency_contacts
            ADD COLUMN telegram_chat_id TEXT
        """)


    cursor.execute("""
        PRAGMA table_info(sos_events)
    """)

    sos_table_info = cursor.fetchall()

    sos_columns = [
        column["name"]
        for column in sos_table_info
    ]

    if "user_id" not in sos_columns:

        cursor.execute("""
            ALTER TABLE sos_events
            ADD COLUMN user_id INTEGER
        """)

    # Check if latitude has NOT NULL constraint and migrate if needed
    lat_col = next((c for c in sos_table_info if c["name"] == "latitude"), None)
    if lat_col and lat_col["notnull"] == 1:
        cursor.execute("ALTER TABLE sos_events RENAME TO sos_events_old")
        cursor.execute("""
            CREATE TABLE sos_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                latitude REAL,
                longitude REAL,
                maps_url TEXT,
                trigger_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            INSERT INTO sos_events (id, user_id, latitude, longitude, maps_url, trigger_type, status, created_at)
            SELECT id, user_id, latitude, longitude, maps_url, trigger_type, status, created_at
            FROM sos_events_old
        """)
        cursor.execute("DROP TABLE sos_events_old")

    # --------------------------------------------------------
    # PHASE 6 MIGRATIONS & SCHEMA EXTENSIONS
    # --------------------------------------------------------
    # 1. Add priority to emergency_contacts (1=Primary, 2=Secondary, 3=Backup)
    cursor.execute("PRAGMA table_info(emergency_contacts)")
    curr_contact_cols = [c["name"] for c in cursor.fetchall()]
    if "priority" not in curr_contact_cols:
        cursor.execute("ALTER TABLE emergency_contacts ADD COLUMN priority INTEGER DEFAULT 1")

    # 2. Add escalation & acknowledgement tracking to sos_events
    cursor.execute("PRAGMA table_info(sos_events)")
    curr_sos_cols = [c["name"] for c in cursor.fetchall()]
    if "escalation_level" not in curr_sos_cols:
        cursor.execute("ALTER TABLE sos_events ADD COLUMN escalation_level INTEGER DEFAULT 1")
    if "acknowledged_at" not in curr_sos_cols:
        cursor.execute("ALTER TABLE sos_events ADD COLUMN acknowledged_at TIMESTAMP")
    if "acknowledged_by" not in curr_sos_cols:
        cursor.execute("ALTER TABLE sos_events ADD COLUMN acknowledged_by TEXT")

    # 3. Create sos_location_breadcrumbs table for continuous live tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sos_location_breadcrumbs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sos_event_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            accuracy REAL,
            speed REAL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sos_event_id) REFERENCES sos_events(id) ON DELETE CASCADE
        )
    """)

    # 4. Create safety_checkins table for dead-man's switch / periodic welfare timer
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS safety_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    connection.commit()

    connection.close()


# ============================================================
# USERS
# ============================================================

def create_user(
    name,
    email,
    password_hash
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO users (
            name,
            email,
            password_hash
        )

        VALUES (?, ?, ?)
    """, (
        name,
        email,
        password_hash
    ))

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id


def get_user_by_email(email):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            password_hash,
            camera_permission,
            microphone_permission,
            location_permission,
            protection_enabled,
            created_at

        FROM users

        WHERE email = ?

        LIMIT 1
    """, (
        email,
    ))

    user = cursor.fetchone()

    connection.close()

    if user:

        return dict(user)

    return None


def get_user_by_id(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            camera_permission,
            microphone_permission,
            location_permission,
            protection_enabled,
            created_at

        FROM users

        WHERE id = ?

        LIMIT 1
    """, (
        user_id,
    ))

    user = cursor.fetchone()

    connection.close()

    if user:

        return dict(user)

    return None


def update_permissions(
    user_id,
    camera_permission,
    microphone_permission,
    location_permission
):

    protection_enabled = (
        1
        if (
            camera_permission
            and microphone_permission
            and location_permission
        )
        else 0
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users

        SET
            camera_permission = ?,
            microphone_permission = ?,
            location_permission = ?,
            protection_enabled = ?

        WHERE id = ?
    """, (
        int(bool(camera_permission)),
        int(bool(microphone_permission)),
        int(bool(location_permission)),
        protection_enabled,
        user_id
    ))

    connection.commit()

    connection.close()

    return True


# ============================================================
# EMERGENCY CONTACTS
# ============================================================

def get_contacts(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            phone,
            telegram_chat_id,
            COALESCE(priority, 1) AS priority,
            created_at

        FROM emergency_contacts

        WHERE user_id = ?

        ORDER BY COALESCE(priority, 1) ASC, id DESC
    """, (
        user_id,
    ))

    contacts = cursor.fetchall()

    connection.close()

    return [
        dict(contact)
        for contact in contacts
    ]


def add_contact(
    user_id,
    name,
    phone,
    telegram_chat_id=None,
    priority=1
):

    connection = get_connection()

    cursor = connection.cursor()

    priority_val = int(priority) if priority else 1

    cursor.execute("""
        INSERT INTO emergency_contacts (
            user_id,
            name,
            phone,
            telegram_chat_id,
            priority
        )

        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        name,
        phone,
        telegram_chat_id,
        priority_val
    ))

    connection.commit()

    contact_id = cursor.lastrowid

    connection.close()

    return contact_id

    return contact_id


def delete_contact(
    user_id,
    contact_id
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM emergency_contacts

        WHERE id = ?

        AND user_id = ?
    """, (
        contact_id,
        user_id
    ))

    deleted = cursor.rowcount > 0

    connection.commit()

    connection.close()

    return deleted


# ============================================================
# SOS EVENTS
# ============================================================

def create_sos_event(
    user_id,
    latitude,
    longitude,
    maps_url,
    trigger_type,
    status
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sos_events (
            user_id,
            latitude,
            longitude,
            maps_url,
            trigger_type,
            status
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        latitude,
        longitude,
        maps_url,
        trigger_type,
        status
    ))

    connection.commit()

    event_id = cursor.lastrowid

    connection.close()

    return event_id


def update_sos_event_status(sos_event_id, status):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        UPDATE sos_events
        SET status = ?
        WHERE id = ?
    """, (
        status,
        sos_event_id
    ))

    connection.commit()

    connection.close()


def log_notification(
    sos_event_id,
    contact_id,
    channel,
    recipient,
    status,
    provider=None,
    error_message=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO notification_logs (
            sos_event_id,
            contact_id,
            channel,
            recipient,
            status,
            provider,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        sos_event_id,
        contact_id,
        channel,
        recipient,
        status,
        provider,
        error_message
    ))

    connection.commit()

    log_id = cursor.lastrowid

    connection.close()

    return log_id


def get_notification_logs(sos_event_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            nl.id,
            nl.sos_event_id,
            nl.contact_id,
            nl.channel,
            nl.recipient,
            nl.status,
            nl.provider,
            nl.error_message,
            nl.created_at,
            ec.name as contact_name
        FROM notification_logs nl
        LEFT JOIN emergency_contacts ec ON nl.contact_id = ec.id
        WHERE nl.sos_event_id = ?
        ORDER BY nl.id ASC
    """, (
        sos_event_id,
    ))

    logs = cursor.fetchall()

    connection.close()

    return [
        dict(log)
        for log in logs
    ]


def get_sos_events(user_id, include_notifications=True):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            latitude,
            longitude,
            maps_url,
            trigger_type,
            status,
            created_at

        FROM sos_events

        WHERE user_id = ?

        ORDER BY id DESC
    """, (
        user_id,
    ))

    events = [
        dict(event)
        for event in cursor.fetchall()
    ]

    if include_notifications:
        for event in events:
            cursor.execute("""
                SELECT
                    nl.id,
                    nl.channel,
                    nl.recipient,
                    nl.status,
                    nl.provider,
                    nl.error_message,
                    ec.name as contact_name
                FROM notification_logs nl
                LEFT JOIN emergency_contacts ec ON nl.contact_id = ec.id
                WHERE nl.sos_event_id = ?
                ORDER BY nl.id ASC
            """, (event["id"],))

            event["notifications"] = [
                dict(log)
                for log in cursor.fetchall()
            ]

    connection.close()

    return events


# ============================================================
# OLD DEVICE FUNCTIONS
# Kept so the old project doesn't immediately break.
# They are not part of the new architecture.
# ============================================================

def register_device(
    device_token,
    device_name=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO devices (
            device_token,
            device_name
        )

        VALUES (?, ?)
    """, (
        device_token,
        device_name
    ))

    connection.commit()

    device_id = cursor.lastrowid

    connection.close()

    return device_id


def get_devices():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            device_token,
            device_name,
            created_at

        FROM devices

        ORDER BY id DESC
    """)

    devices = cursor.fetchall()

    connection.close()

    return [
        dict(device)
        for device in devices
    ]


# ============================================================
# PHASE 6: INTELLIGENT FEATURES — BREADCRUMBS & LIVE TRACKING
# ============================================================

def add_breadcrumb(sos_event_id, latitude, longitude, accuracy=None, speed=None):
    """Add a live location breadcrumb to an active SOS event."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO sos_location_breadcrumbs (
            sos_event_id,
            latitude,
            longitude,
            accuracy,
            speed
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        sos_event_id,
        float(latitude),
        float(longitude),
        float(accuracy) if accuracy is not None else None,
        float(speed) if speed is not None else None
    ))
    breadcrumb_id = cursor.lastrowid

    # Update latest location and maps URL on the SOS event
    maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
    cursor.execute("""
        UPDATE sos_events
        SET latitude = ?, longitude = ?, maps_url = ?
        WHERE id = ?
    """, (float(latitude), float(longitude), maps_url, sos_event_id))

    connection.commit()
    connection.close()
    return breadcrumb_id


def get_breadcrumbs(sos_event_id):
    """Fetch all location breadcrumbs for an SOS event in chronological order."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, sos_event_id, latitude, longitude, accuracy, speed, recorded_at
        FROM sos_location_breadcrumbs
        WHERE sos_event_id = ?
        ORDER BY id ASC
    """, (sos_event_id,))
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]


# ============================================================
# PHASE 6: EMERGENCY ACKNOWLEDGEMENT & ESCALATION
# ============================================================

def get_sos_event_by_id(sos_event_id):
    """Get single SOS event details with acknowledgement & escalation info."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, user_id, latitude, longitude, maps_url, trigger_type, status,
               COALESCE(escalation_level, 1) AS escalation_level,
               acknowledged_at, acknowledged_by, created_at
        FROM sos_events
        WHERE id = ?
    """, (sos_event_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def acknowledge_sos_event(sos_event_id, acknowledged_by="Guardian"):
    """Mark an SOS event as acknowledged by a guardian or responder."""
    connection = get_connection()
    cursor = connection.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE sos_events
        SET acknowledged_at = ?, acknowledged_by = ?, status = 'acknowledged'
        WHERE id = ?
    """, (now_str, acknowledged_by, sos_event_id))
    connection.commit()
    connection.close()
    return True


def escalate_sos_event_level(sos_event_id):
    """Increment escalation level of an SOS event."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE sos_events
        SET escalation_level = COALESCE(escalation_level, 1) + 1
        WHERE id = ?
    """, (sos_event_id,))
    connection.commit()
    cursor.execute("SELECT escalation_level FROM sos_events WHERE id = ?", (sos_event_id,))
    row = cursor.fetchone()
    new_level = row["escalation_level"] if row else 2
    connection.close()
    return new_level


def get_contacts_by_priority(user_id, priority=None):
    """Fetch contacts filtered by priority tier (1=Primary, 2=Secondary, 3=Backup)."""
    connection = get_connection()
    cursor = connection.cursor()
    if priority is not None:
        cursor.execute("""
            SELECT id, user_id, name, phone, telegram_chat_id,
                   COALESCE(priority, 1) AS priority, created_at
            FROM emergency_contacts
            WHERE user_id = ? AND (priority = ? OR (priority IS NULL AND ? = 1))
            ORDER BY id ASC
        """, (user_id, int(priority), int(priority)))
    else:
        cursor.execute("""
            SELECT id, user_id, name, phone, telegram_chat_id,
                   COALESCE(priority, 1) AS priority, created_at
            FROM emergency_contacts
            WHERE user_id = ?
            ORDER BY COALESCE(priority, 1) ASC, id ASC
        """, (user_id,))
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]


# ============================================================
# PHASE 6: SAFETY CHECK-IN TIMER
# ============================================================

def create_safety_checkin(user_id, duration_minutes, note=None):
    """Create a new safety checkin with an expiration timestamp."""
    connection = get_connection()
    cursor = connection.cursor()
    # Cancel any previous active checkins for this user
    cursor.execute("""
        UPDATE safety_checkins
        SET status = 'cancelled'
        WHERE user_id = ? AND status = 'active'
    """, (user_id,))
    expires_at = (datetime.now() + timedelta(minutes=int(duration_minutes))).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO safety_checkins (user_id, duration_minutes, expires_at, status, note)
        VALUES (?, ?, ?, 'active', ?)
    """, (user_id, int(duration_minutes), expires_at, note))
    checkin_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return {
        "id": checkin_id,
        "user_id": user_id,
        "duration_minutes": int(duration_minutes),
        "expires_at": expires_at,
        "status": "active",
        "note": note
    }


def get_active_safety_checkin(user_id):
    """Get active safety checkin for user if any."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, user_id, duration_minutes, expires_at, status, note, created_at
        FROM safety_checkins
        WHERE user_id = ? AND status = 'active'
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def complete_safety_checkin(checkin_id, user_id, status="checked_in"):
    """Mark safety checkin as checked_in or expired_triggered."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE safety_checkins
        SET status = ?
        WHERE id = ? AND user_id = ?
    """, (status, checkin_id, user_id))
    connection.commit()
    connection.close()
    return True
