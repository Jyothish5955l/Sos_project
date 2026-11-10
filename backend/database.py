import sqlite3
import os


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
            created_at

        FROM emergency_contacts

        WHERE user_id = ?

        ORDER BY id DESC
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
    telegram_chat_id=None
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO emergency_contacts (
            user_id,
            name,
            phone,
            telegram_chat_id
        )

        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        name,
        phone,
        telegram_chat_id
    ))

    connection.commit()

    contact_id = cursor.lastrowid

    connection.close()

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


def get_sos_events(user_id):

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

    events = cursor.fetchall()

    connection.close()

    return [
        dict(event)
        for event in events
    ]


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