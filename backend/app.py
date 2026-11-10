import os
import sys
import re
from datetime import datetime, timedelta

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.getenv("ENV_FILE", ".env")))

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

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
    add_breadcrumb,
    get_breadcrumbs,
    get_sos_event_by_id,
    acknowledge_sos_event,
    escalate_sos_event_level,
    create_safety_checkin,
    get_active_safety_checkin,
    complete_safety_checkin,
    get_contacts_by_priority
)

from notifications import notification_service
from rate_limiter import rate_limiter


# ============================================================
# APPLICATION CONFIGURATION & SECURITY HYGIENE
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

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.getenv("FLASK_ENV") == "production"
        or os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1")
    ),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,  # 2MB payload protection
    SEND_FILE_MAX_AGE_DEFAULT=int(os.getenv("STATIC_CACHE_SECONDS", "3600"))
)

# Enable ProxyFix middleware for reverse proxies (Render, Nginx, Cloudflare, ALB)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=int(os.getenv("PROXY_FIX_FOR", "1")),
    x_proto=int(os.getenv("PROXY_FIX_PROTO", "1")),
    x_host=int(os.getenv("PROXY_FIX_HOST", "1")),
    x_prefix=int(os.getenv("PROXY_FIX_PREFIX", "1"))
)

# Idempotently ensure database schema is initialized on application startup
try:
    initialize_database()
except Exception as _db_init_err:
    print(f"Warning: Database startup check: {_db_init_err}")

CORS(app)


# ============================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=(self)"
    return response


# ============================================================
# RATE LIMITING HELPER
# ============================================================

def check_rate_limit(key: str, max_requests: int, window_seconds: int):
    allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
    if not allowed:
        response = jsonify({
            "success": False,
            "message": f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
            "retry_after": retry_after
        })
        response.headers["Retry-After"] = str(retry_after)
        return response, 429
    return None


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
# HEALTH CHECKS & SYSTEM DIAGNOSTICS
# ============================================================

@app.route("/health", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health():
    db_status = "connected"
    try:
        from database import get_connection
        conn = get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    sms_provider = os.getenv("SMS_PROVIDER", "mock").lower()
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_status = "configured" if telegram_token and not telegram_token.startswith("YOUR_") else "simulated"

    is_healthy = db_status == "connected"
    status_code = 200 if is_healthy else 503

    return jsonify({
        "success": is_healthy,
        "status": "healthy" if is_healthy else "degraded",
        "service": "SOS Guardian",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            "database": db_status,
            "sms_provider": sms_provider,
            "telegram": telegram_status,
            "rate_limiter": "active"
        }
    }), status_code


@app.route("/robots.txt", methods=["GET"])
def robots_txt():
    return "User-agent: *\nDisallow: /api/\n", 200, {"Content-Type": "text/plain"}


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

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        rate_resp = check_rate_limit(f"register:{client_ip}", max_requests=10, window_seconds=60)
        if rate_resp:
            return rate_resp

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

        if len(name) < 2 or len(name) > 60:
            return jsonify({
                "success": False,
                "message": "Name must be between 2 and 60 characters"
            }), 400

        if not email:
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400

        EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(EMAIL_REGEX, email):
            return jsonify({
                "success": False,
                "message": "Enter a valid email address"
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must contain at least 6 characters"
            }), 400

        if len(password) > 128:
            return jsonify({
                "success": False,
                "message": "Password cannot exceed 128 characters"
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
                "message": "An account with this email already exists"
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
        session.permanent = True


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
        # RATE LIMITING & VALIDATION
        # ----------------------------------------------------

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        rate_key = f"login:{client_ip}:{email or 'unknown'}"

        rate_resp = check_rate_limit(rate_key, max_requests=5, window_seconds=60)
        if rate_resp:
            return rate_resp

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

        # Reset rate limiter upon successful authentication
        rate_limiter.reset(rate_key)

        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        session["user_id"] = user["id"]
        session.permanent = True


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

        raw_priority = data.get("priority", 1)
        try:
            priority = int(raw_priority)
            if priority not in [1, 2, 3]:
                priority = 1
        except (ValueError, TypeError):
            priority = 1


        if not name or len(name) < 1 or len(name) > 60:

            return jsonify({

                "success": False,

                "message":
                    "Contact name must be between 1 and 60 characters"

            }), 400

        PHONE_REGEX = r"^\+?[0-9\s\-()]{7,20}$"
        if not phone or not re.match(PHONE_REGEX, phone):

            return jsonify({

                "success": False,

                "message":
                    "Enter a valid phone number (7-20 digits)"

            }), 400

        TG_REGEX = r"^@?[a-zA-Z0-9_]{4,64}$|^-?[0-9]{5,20}$"
        if telegram_chat_id and not re.match(TG_REGEX, telegram_chat_id):

            return jsonify({

                "success": False,

                "message":
                    "Enter a valid Telegram username (@handle) or numeric Chat ID"

            }), 400

        existing_contacts = get_contacts(session["user_id"])
        if len(existing_contacts) >= 20:

            return jsonify({

                "success": False,

                "message":
                    "Maximum contact limit reached (20 contacts max)"

            }), 400


        contact_id = add_contact(

            session["user_id"],

            name,

            phone,

            telegram_chat_id,

            priority
        )


        return jsonify({

            "success": True,

            "message":
                "Emergency contact added successfully",

            "contact_id":
                contact_id,

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
        import traceback
        traceback.print_exc()
        print(
            f"Error creating contact: {error}"
        )

        return jsonify({
            "success": False,
            "message": f"Failed to create emergency contact: {str(error)}"
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

        rate_resp = check_rate_limit(f"test_contact:{session['user_id']}", max_requests=5, window_seconds=60)
        if rate_resp:
            return rate_resp

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

        rate_resp = check_rate_limit(f"sos:{session['user_id']}", max_requests=1, window_seconds=3)
        if rate_resp:
            return rate_resp

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

        ALLOWED_TRIGGERS = {"manual", "hand_gesture", "voice", "fall_detection", "safety_checkin"}
        if trigger_type not in ALLOWED_TRIGGERS:
            return jsonify({
                "success": False,
                "message": "Invalid trigger_type. Must be manual, hand_gesture, voice, fall_detection, or safety_checkin"
            }), 400


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

        # Record initial location breadcrumb if GPS available
        if has_location:
            try:
                add_breadcrumb(
                    event_id,
                    latitude,
                    longitude,
                    accuracy=data.get("accuracy"),
                    speed=data.get("speed")
                )
            except Exception as e_bc:
                print(f"Initial breadcrumb error: {e_bc}")


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

            "event_id":
                event_id,

            "tracking_url":
                f"/api/sos/{event_id}/tracking",

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
# PHASE 6: INTELLIGENT FEATURES — LIVE TRACKING & BREADCRUMBS
# ============================================================

@app.route(
    "/api/sos/<int:event_id>/location",
    methods=["POST"]
)
def update_sos_location(event_id):
    """
    Continuous live location streaming endpoint.
    Appends location breadcrumb to active emergency event.
    """
    event = get_sos_event_by_id(event_id)
    if not event:
        return jsonify({"success": False, "message": "SOS event not found"}), 404

    data = request.get_json() or {}
    lat = data.get("latitude")
    lng = data.get("longitude")
    accuracy = data.get("accuracy")
    speed = data.get("speed")

    if lat is None or lng is None:
        return jsonify({"success": False, "message": "latitude and longitude required"}), 400

    try:
        lat_f = float(lat)
        lng_f = float(lng)
        if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
            return jsonify({"success": False, "message": "Coordinates out of bounds"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid numeric coordinates"}), 400

    breadcrumb_id = add_breadcrumb(event_id, lat_f, lng_f, accuracy=accuracy, speed=speed)
    maps_url = f"https://www.google.com/maps?q={lat_f},{lng_f}"

    return jsonify({
        "success": True,
        "event_id": event_id,
        "breadcrumb_id": breadcrumb_id,
        "latitude": lat_f,
        "longitude": lng_f,
        "maps_url": maps_url,
        "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200


@app.route(
    "/api/sos/<int:event_id>/tracking",
    methods=["GET"]
)
def get_sos_tracking(event_id):
    """
    Live emergency tracking view for responders and guardians.
    Returns latest GPS pin, breadcrumb history, trigger type, and status.
    """
    event = get_sos_event_by_id(event_id)
    if not event:
        return jsonify({"success": False, "message": "SOS event not found"}), 404

    user = get_user_by_id(event["user_id"])
    breadcrumbs = get_breadcrumbs(event_id)

    return jsonify({
        "success": True,
        "event_id": event_id,
        "user_name": user["name"] if user else "SOS User",
        "trigger_type": event["trigger_type"],
        "status": event["status"],
        "escalation_level": event.get("escalation_level", 1),
        "acknowledged_at": event.get("acknowledged_at"),
        "acknowledged_by": event.get("acknowledged_by"),
        "latest_location": {
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "maps_url": event["maps_url"]
        },
        "breadcrumbs_count": len(breadcrumbs),
        "breadcrumbs": breadcrumbs,
        "created_at": event["created_at"]
    }), 200


# ============================================================
# PHASE 6: EMERGENCY ACKNOWLEDGEMENT & ESCALATION
# ============================================================

@app.route(
    "/api/sos/<int:event_id>/acknowledge",
    methods=["POST"]
)
def acknowledge_sos(event_id):
    """
    Acknowledge receipt of emergency alert by a guardian or responder.
    Halts further escalation.
    """
    event = get_sos_event_by_id(event_id)
    if not event:
        return jsonify({"success": False, "message": "SOS event not found"}), 404

    data = request.get_json() or {}
    acknowledged_by = (data.get("acknowledged_by") or data.get("responder_name") or "Guardian").strip()[:80]

    acknowledge_sos_event(event_id, acknowledged_by=acknowledged_by)
    updated_event = get_sos_event_by_id(event_id)

    return jsonify({
        "success": True,
        "message": f"Emergency alert acknowledged by {acknowledged_by}",
        "status": updated_event["status"] if updated_event else "acknowledged",
        "acknowledged_by": acknowledged_by,
        "event": updated_event
    }), 200


@app.route(
    "/api/sos/<int:event_id>/escalate",
    methods=["POST"]
)
def escalate_sos(event_id):
    """
    Escalate unacknowledged emergency alert to higher priority contacts.
    """
    rate_resp = check_rate_limit(f"escalate:{event_id}", max_requests=5, window_seconds=60)
    if rate_resp:
        return rate_resp

    event = get_sos_event_by_id(event_id)
    if not event:
        return jsonify({"success": False, "message": "SOS event not found"}), 404

    if event.get("status") == "acknowledged":
        return jsonify({
            "success": False,
            "message": "Emergency event has already been acknowledged."
        }), 400

    new_level = escalate_sos_event_level(event_id)
    user = get_user_by_id(event["user_id"])
    user_name = user["name"] if user else "SOS Guardian User"

    # Query contacts: prefer secondary/backup tiers if defined, else all contacts
    tier_contacts = get_contacts_by_priority(event["user_id"], priority=min(new_level, 3))
    if not tier_contacts:
        tier_contacts = get_contacts(event["user_id"])

    report = notification_service.send_escalation_alerts(
        sos_event_id=event_id,
        user_name=user_name,
        escalation_level=new_level,
        latitude=event["latitude"],
        longitude=event["longitude"],
        maps_url=event["maps_url"],
        contacts=tier_contacts
    )

    return jsonify({
        "success": True,
        "event_id": event_id,
        "escalation_level": new_level,
        "dispatches": report.get("dispatches", [])
    }), 200


# ============================================================
# PHASE 6: SAFETY CHECK-IN TIMER
# ============================================================

@app.route(
    "/api/safety-checkin/start",
    methods=["POST"]
)
@login_required
def start_safety_checkin():
    """Start a periodic welfare / safety check-in timer."""
    data = request.get_json() or {}
    duration = data.get("duration_minutes", 15)
    note = (data.get("note") or "").strip()[:200]

    try:
        dur_int = int(duration)
        if dur_int < 1 or dur_int > 1440:
            return jsonify({"success": False, "message": "Duration must be between 1 and 1440 minutes"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid duration"}), 400

    checkin = create_safety_checkin(session["user_id"], dur_int, note=note)
    return jsonify({"success": True, "checkin": checkin}), 201


@app.route(
    "/api/safety-checkin/status",
    methods=["GET"]
)
@login_required
def safety_checkin_status():
    """Get active safety checkin for the authenticated user."""
    checkin = get_active_safety_checkin(session["user_id"])
    if not checkin:
        return jsonify({"success": True, "active": False, "checkin": None}), 200

    exp_dt = datetime.strptime(checkin["expires_at"], "%Y-%m-%d %H:%M:%S")
    remaining_seconds = max(0, int((exp_dt - datetime.now()).total_seconds()))

    return jsonify({
        "success": True,
        "active": True,
        "checkin": checkin,
        "remaining_seconds": remaining_seconds,
        "is_expired": remaining_seconds == 0
    }), 200


@app.route(
    "/api/safety-checkin/checkin",
    methods=["POST"]
)
@login_required
def confirm_safety_checkin():
    """User confirms they are safe, completing the check-in."""
    checkin = get_active_safety_checkin(session["user_id"])
    if not checkin:
        return jsonify({"success": False, "message": "No active safety check-in found"}), 404

    complete_safety_checkin(checkin["id"], session["user_id"], status="checked_in")
    return jsonify({
        "success": True,
        "message": "Safety check-in completed. You are recorded as safe."
    }), 200


@app.route(
    "/api/safety-checkin/trigger-expired",
    methods=["POST"]
)
@login_required
def trigger_expired_checkin():
    """
    Triggered when a safety checkin timer expires without user confirmation.
    Dispatches emergency SOS alert with 'safety_checkin' trigger.
    """
    checkin = get_active_safety_checkin(session["user_id"])
    data = request.get_json() or {}
    lat = data.get("latitude")
    lng = data.get("longitude")

    note_text = f" (Note: {checkin['note']})" if checkin and checkin.get("note") else ""
    user = get_user_by_id(session["user_id"])
    user_name = user["name"] if user else "SOS Guardian User"

    has_loc = False
    maps_url = None
    if lat is not None and lng is not None:
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
                has_loc = True
                maps_url = f"https://www.google.com/maps?q={lat_f},{lng_f}"
        except (ValueError, TypeError):
            pass

    event_id = create_sos_event(
        session["user_id"],
        float(lat) if has_loc else None,
        float(lng) if has_loc else None,
        maps_url,
        "safety_checkin",
        "received"
    )

    if checkin:
        complete_safety_checkin(checkin["id"], session["user_id"], status="expired_triggered")

    contacts = get_contacts(session["user_id"])
    delivery_report = notification_service.send_emergency_alerts(
        sos_event_id=event_id,
        user_name=f"{user_name} [Missed Safety Check-in{note_text}]",
        trigger_type="safety_checkin",
        latitude=float(lat) if has_loc else None,
        longitude=float(lng) if has_loc else None,
        maps_url=maps_url,
        contacts=contacts,
        user_id=session["user_id"]
    )

    return jsonify({
        "success": True,
        "message": "Emergency alert triggered due to missed safety check-in",
        "event_id": event_id,
        "delivery": delivery_report
    }), 200


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