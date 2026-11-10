import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from functools import wraps


from database import (
    initialize_database,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_permissions,
    get_contacts,
    add_contact,
    delete_contact,
    create_sos_event,
    get_sos_events,
    get_notification_logs,
)

from notifications import notification_service


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
    static_url_path="/static"
)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "SOS_GUARDIAN_CHANGE_THIS_SECRET_KEY"
)

CORS(app)


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401

        return function(*args, **kwargs)

    return wrapper


def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return None

    return get_user_by_id(user_id)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "status": "healthy",
        "service": "SOS Guardian"
    })


# ============================================================
# HAND GESTURE DETECTION (CLIENT-SIDE TELEMETRY)
# ============================================================

@app.route(
    "/api/gesture/detect",
    methods=["POST"]
)
@login_required
def detect_gesture():

    # Hand gesture recognition runs client-side in the browser via MediaPipe Tasks Vision.
    return jsonify({
        "success": True,
        "message": "Client-side MediaPipe gesture detection is active.",
        "client_side_required": True
    }), 200


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/api/auth/register",
    methods=["POST"]
)
def register():

    try:

        data = request.get_json() or {}


        name = data.get(
            "name",
            ""
        ).strip()


        email = data.get(
            "email",
            ""
        ).strip().lower()


        password = data.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name:

            return jsonify({
                "success": False,
                "message": "Name is required"
            }), 400


        if not email:

            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400


        if "@" not in email:

            return jsonify({
                "success": False,
                "message": "Enter a valid email address"
            }), 400


        if len(password) < 6:

            return jsonify({
                "success": False,
                "message":
                    "Password must contain at least 6 characters"
            }), 400


        # ----------------------------------------------------
        # CHECK EXISTING USER
        # ----------------------------------------------------

        existing_user = get_user_by_email(
            email
        )


        if existing_user:

            return jsonify({
                "success": False,
                "message":
                    "An account with this email already exists"
            }), 409


        # ----------------------------------------------------
        # HASH PASSWORD
        # ----------------------------------------------------

        password_hash = generate_password_hash(
            password
        )


        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        user_id = create_user(
            name,
            email,
            password_hash
        )


        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session["user_id"] = user_id


        return jsonify({

            "success": True,

            "message":
                "Account created successfully",

            "user": {

                "id": user_id,

                "name": name,

                "email": email,

                "protection_enabled": False
            }

        }), 201


    except Exception as error:

        print(
            f"Registration error: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to create account"

        }), 500


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/api/auth/login",
    methods=["POST"]
)
def login():

    try:

        data = request.get_json() or {}


        email = data.get(
            "email",
            ""
        ).strip().lower()


        password = data.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not email or not password:

            return jsonify({

                "success": False,

                "message":
                    "Email and password are required"

            }), 400


        # ----------------------------------------------------
        # FIND USER
        # ----------------------------------------------------

        user = get_user_by_email(
            email
        )


        if not user:

            return jsonify({

                "success": False,

                "message":
                    "Invalid email or password"

            }), 401


        # ----------------------------------------------------
        # CHECK PASSWORD
        # ----------------------------------------------------

        if not check_password_hash(

            user["password_hash"],

            password

        ):

            return jsonify({

                "success": False,

                "message":
                    "Invalid email or password"

            }), 401


        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session["user_id"] = user["id"]


        return jsonify({

            "success": True,

            "message":
                "Login successful",

            "user": {

                "id":
                    user["id"],

                "name":
                    user["name"],

                "email":
                    user["email"],

                "protection_enabled":
                    bool(
                        user["protection_enabled"]
                    )
            }

        })


    except Exception as error:

        print(
            f"Login error: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Login failed"

        }), 500


# ============================================================
# LOGOUT
# ============================================================

@app.route(
    "/api/auth/logout",
    methods=["POST"]
)
def logout():

    session.clear()


    return jsonify({

        "success": True,

        "message":
            "Logged out successfully"

    })


# ============================================================
# CURRENT USER
# ============================================================

@app.route(
    "/api/auth/me",
    methods=["GET"]
)
def get_current_user():

    user = current_user()


    if not user:

        return jsonify({

            "success": False,

            "authenticated": False

        }), 401


    return jsonify({

        "success": True,

        "authenticated": True,

        "user": {

            "id":
                user["id"],

            "name":
                user["name"],

            "email":
                user["email"],

            "protection_enabled":
                bool(
                    user["protection_enabled"]
                )
        }

    })


# ============================================================
# SAVE PERMISSIONS
# ============================================================

@app.route(
    "/api/auth/permissions",
    methods=["POST"]
)
@login_required
def save_permissions():

    try:

        data = request.get_json() or {}


        camera = bool(
            data.get(
                "camera_permission",
                False
            )
        )


        microphone = bool(
            data.get(
                "microphone_permission",
                False
            )
        )


        location = bool(
            data.get(
                "location_permission",
                False
            )
        )


        update_permissions(

            session["user_id"],

            camera,

            microphone,

            location
        )


        user = get_user_by_id(
            session["user_id"]
        )


        return jsonify({

            "success": True,

            "message":
                "Emergency protection settings saved",

            "protection_enabled":
                bool(
                    user["protection_enabled"]
                )

        })


    except Exception as error:

        print(
            f"Permission error: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to save protection settings"

        }), 500


# ============================================================
# EMERGENCY CONTACTS - GET
# ============================================================

@app.route(
    "/api/contacts",
    methods=["GET"]
)
@login_required
def get_all_contacts():

    try:

        contacts = get_contacts(
            session["user_id"]
        )


        return jsonify({

            "success": True,

            "contacts": contacts

        })


    except Exception as error:

        print(
            f"Error loading contacts: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to load emergency contacts"

        }), 500


# ============================================================
# EMERGENCY CONTACTS - ADD
# ============================================================

@app.route(
    "/api/contacts",
    methods=["POST"]
)
@login_required
def create_contact():

    try:

        data = request.get_json() or {}


        name = data.get(
            "name",
            ""
        ).strip()


        phone = data.get(
            "phone",
            ""
        ).strip()

        telegram_chat_id = (
            data.get(
                "telegram_chat_id",
                ""
            ) or ""
        ).strip() or None


        if not name:

            return jsonify({

                "success": False,

                "message":
                    "Contact name is required"

            }), 400


        if not phone:

            return jsonify({

                "success": False,

                "message":
                    "Phone number is required"

            }), 400


        contact_id = add_contact(

            session["user_id"],

            name,

            phone,

            telegram_chat_id
        )


        return jsonify({

            "success": True,

            "message":
                "Emergency contact added successfully",

            "contact": {

                "id":
                    contact_id,

                "name":
                    name,

                "phone":
                    phone,

                "telegram_chat_id":
                    telegram_chat_id

            }

        }), 201


    except Exception as error:

        print(
            f"Error creating contact: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to create emergency contact"

        }), 500


# ============================================================
# EMERGENCY CONTACTS - DELETE
# ============================================================

@app.route(
    "/api/contacts/<int:contact_id>",
    methods=["DELETE"]
)
@login_required
def remove_contact(
    contact_id
):

    try:

        deleted = delete_contact(

            session["user_id"],

            contact_id
        )


        if not deleted:

            return jsonify({

                "success": False,

                "message":
                    "Contact not found"

            }), 404


        return jsonify({

            "success": True,

            "message":
                "Contact deleted successfully"

        })


    except Exception as error:

        print(
            f"Delete contact error: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to delete contact"

        }), 500


# ============================================================
# TEST CONTACT NOTIFICATION
# ============================================================

@app.route(
    "/api/contacts/<int:contact_id>/test",
    methods=["POST"]
)
@login_required
def test_contact_notification(
    contact_id
):

    try:

        contacts = get_contacts(
            session["user_id"]
        )

        contact = next(
            (c for c in contacts if c["id"] == contact_id),
            None
        )

        if not contact:

            return jsonify({

                "success": False,

                "message":
                    "Contact not found"

            }), 404

        user = get_user_by_id(
            session["user_id"]
        )

        user_name = (
            user["name"]
            if user
            else "You"
        )

        results = notification_service.send_test_notification(
            contact,
            user_name
        )

        return jsonify({

            "success": True,

            "message":
                f"Test notification dispatched to {contact['name']}",

            "results":
                results

        }), 200

    except Exception as error:

        print(
            f"Test contact error: {error}"
        )

        return jsonify({

            "success": False,

            "message":
                "Failed to send test alert"

        }), 500


# ============================================================
# SOS
# ============================================================

@app.route(
    "/api/sos",
    methods=["POST"]
)
@login_required
def sos():

    try:

        data = request.get_json() or {}


        latitude = data.get(
            "latitude"
        )


        longitude = data.get(
            "longitude"
        )


        # ----------------------------------------------------
        # LOCATION VALIDATION (OPTIONAL FOR EMERGENCY RESILIENCE)
        # ----------------------------------------------------

        has_location = False

        if latitude is not None and longitude is not None:
            try:
                lat_float = float(latitude)
                lng_float = float(longitude)

                if -90 <= lat_float <= 90 and -180 <= lng_float <= 180:
                    latitude = lat_float
                    longitude = lng_float
                    has_location = True
                else:
                    latitude = None
                    longitude = None
            except (ValueError, TypeError):
                latitude = None
                longitude = None
        else:
            latitude = None
            longitude = None


        # ----------------------------------------------------
        # TRIGGER TYPE
        # ----------------------------------------------------

        trigger_type = data.get(
            "trigger_type",
            "manual"
        )

        if trigger_type == "button":
            trigger_type = "manual"


        # ----------------------------------------------------
        # GOOGLE MAPS URL & LOCATION TEXT
        # ----------------------------------------------------

        if has_location:
            maps_url = (
                "https://www.google.com/maps?q="
                f"{latitude},{longitude}"
            )
            location_text = f"📍 Location:\n{maps_url}"
        else:
            maps_url = None
            location_text = "📍 Location: Unavailable (User GPS disabled or signal lost)"


        status = "received"


        # ----------------------------------------------------
        # SAVE SOS EVENT
        # ----------------------------------------------------

        event_id = create_sos_event(

            session["user_id"],

            latitude,

            longitude,

            maps_url,

            trigger_type,

            status
        )


        # ----------------------------------------------------
        # GET EMERGENCY CONTACTS
        # ----------------------------------------------------

        contacts = get_contacts(

            session["user_id"]
        )


        # ----------------------------------------------------
        # MULTI-CHANNEL EMERGENCY NOTIFICATIONS
        # ----------------------------------------------------

        user = get_user_by_id(session["user_id"])
        user_name = user["name"] if user else "SOS Guardian User"

        delivery_report = notification_service.send_emergency_alerts(
            sos_event_id=event_id,
            user_name=user_name,
            trigger_type=trigger_type,
            latitude=latitude,
            longitude=longitude,
            maps_url=maps_url,
            contacts=contacts
        )

        status = delivery_report.get("overall_status", "notification_sent")


        # ----------------------------------------------------
        # SERVER LOG
        # ----------------------------------------------------

        summary = delivery_report.get("summary", {})

        print()

        print("=" * 50)

        print(
            "🚨 SOS PROCESSING COMPLETE"
        )

        print("=" * 50)

        print(
            f"🆔 Event ID : {event_id}"
        )

        print(
            f"📍 Latitude : {latitude}"
        )

        print(
            f"📍 Longitude: {longitude}"
        )

        print(
            f"🗺️ Maps     : {maps_url}"
        )

        print(
            f"⚡ Trigger  : {trigger_type}"
        )

        print(
            f"👥 Contacts : {len(contacts)}"
        )

        print(
            f"📊 Status   : {status}"
        )

        print(
            f"📱 SMS      : sent={summary.get('sms_sent', 0)}, sim={summary.get('sms_simulated', 0)}, fail={summary.get('sms_failed', 0)}"
        )

        print(
            f"✈️ Telegram : sent={summary.get('telegram_sent', 0)}, sim={summary.get('telegram_simulated', 0)}, fail={summary.get('telegram_failed', 0)}"
        )

        print("=" * 50)

        print()


        return jsonify({

            "success": True,

            "message":
                "SOS processed successfully",

            "event": {

                "id":
                    event_id,

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "maps_url":
                    maps_url,

                "trigger_type":
                    trigger_type,

                "status":
                    status,

                "location_available":
                    has_location
            },

            "notifications": {

                "total_contacts":
                    len(contacts),

                "overall_status":
                    status,

                "summary":
                    summary,

                "results":
                    delivery_report.get("dispatches", [])
            }

        }), 200


    except Exception as error:

        print(
            f"SOS ERROR: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to process SOS request"

        }), 500


# ============================================================
# SOS HISTORY
# ============================================================

@app.route(
    "/api/sos/history",
    methods=["GET"]
)
@login_required
def sos_history():

    try:

        events = get_sos_events(

            session["user_id"]
        )


        return jsonify({

            "success": True,

            "count":
                len(events),

            "events":
                events

        })


    except Exception as error:

        print(
            f"Error loading SOS history: {error}"
        )


        return jsonify({

            "success": False,

            "message":
                "Failed to load SOS history"

        }), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 50)

    print("🛡️ SOS GUARDIAN")

    print("=" * 50)


    print(
        "Initializing database..."
    )


    initialize_database()


    print(
        "✅ Database ready"
    )


    print(
        "🚀 Starting Flask server..."
    )


    print("=" * 50)


    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )