# SPEC.md — SOS Guardian Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: Phase 0 specification finalized. Implementation proceeds strictly phase-by-phase upon explicit user approval.

---

## 1. Vision

**SOS Guardian** is a web-based, life-critical emergency assistance application engineered to provide fast, reliable, multi-modal emergency alert dispatching. Users can trigger an emergency alert via:
1. **Manual SOS** (one-tap trigger with visual/audible 5-second countdown and instant cancellation).
2. **Open-Palm Hand Gesture Detection** (computer vision in the browser via MediaPipe Tasks Vision HandLandmarker).
3. **Voice Emergency Commands** (hands-free audio recognition via browser Web Speech API for predefined distress keywords).

Upon trigger activation, the system acquires GPS coordinates (if available), persists the emergency event in SQLite, and dispatches real-time alerts across configured communication channels (Telegram Bot API, SMS provider, Push/FCM).

---

## 2. Core Functional Requirements (Modules A–J)

### Module A — User Authentication & Session Security
- User registration with name, email, and password.
- Password hashing using standard Werkzeug/bcrypt algorithms.
- Session or token-based authentication protecting all private API endpoints.
- User-level data isolation: strictly prevent cross-user contact or SOS history data leaks.
- Persisted device and permission states (camera, microphone, location, protection status).

### Module B — Main Dashboard & Readiness Telemetry
- Unified, responsive dashboard displaying real-time system readiness indicators:
  - Camera & gesture detection readiness.
  - Microphone & voice recognition status.
  - Geolocation permission & accuracy status.
  - Emergency contact configuration count & health.
- Visual and audible countdown interface with 5-second abort window.
- Immediate feedback reflecting actual system and delivery states.

### Module C — Manual SOS Engine
- Prominent, high-contrast, accessible SOS emergency button.
- 5-second countdown with visible progress indicator and immediate abort capability.
- Duplicate submission prevention and idempotent request processing.
- Handles missing or delayed GPS coordinates without failing or blocking alert dispatch.

### Module D — Open-Palm Hand Gesture Detection
- Client-side execution in the browser using MediaPipe Tasks Vision (`HandLandmarker`).
- Strict palm landmark evaluation:
  - Extension of all five digits (thumb, index, middle, ring, pinky) evaluated against joint and wrist geometry.
  - Discrimination against closed fists, resting hands, waving, and partial finger extensions.
  - 2-second temporal stability window before triggering the 5-second SOS countdown.
  - Post-trigger cooldown period to prevent runaway trigger loops.
- Camera and model lifecycle management: clear error states for camera permission denied, hardware unavailable, or model loading failure.

### Module E — Voice SOS Recognition
- Speech recognition via browser Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`).
- Supported emergency phrases: "SOS", "Help me", "Emergency".
- Continuous listening with error recovery and reconnection handling.
- Triggers standard 5-second countdown with cancellation window.
- Cooldown and false-positive mitigation.

### Module F — Geolocation Capture & Resilience
- Capture latitude and longitude via browser Geolocation API (`getCurrentPosition`).
- Generate standard Google Maps URL: `https://www.google.com/maps?q={lat},{lng}`.
- Graceful degradation: Geolocation failure or permission denial must NOT block the SOS event creation or notification dispatch.

### Module G — Emergency Contact Management
- Full CRUD operations for user emergency contacts (Name, Phone number, optional Telegram Chat ID).
- Validation of phone numbers (E.164 standard recommended).
- Association of contacts strictly to authenticated user ID.

### Module H — Central SOS Engine
- Single unified backend emergency processing pipeline for all trigger types (`manual`, `hand_gesture`, `voice`).
- Idempotency and de-duplication within temporal threshold.
- Atomic creation and persistence of `sos_events` record in SQLite.
- Immediate dispatch of notification tasks across active providers.
- Comprehensive response containing event ID, timestamp, trigger type, and provider dispatch results.

### Module I — Emergency Notification Multi-Channel System
- **Telegram Bot API**: Secure backend integration sending distress messages with maps link to configured Telegram chat IDs.
- **SMS Provider Interface**: Pluggable provider abstraction for SMS delivery.
- **Push Notifications**: Firebase Cloud Messaging (FCM) integration where supported.
- Explicit notification status tracking per channel: `Pending`, `Sent`, `Failed`, or `Confirmed`. No false claims of delivery.

### Module J — SOS History & Audit Trail
- Secure query of past emergency events for authenticated user.
- Recorded attributes: Event ID, user ID, trigger type, timestamp, coordinates, Google Maps link, status, and notification results.

---

## 3. Technology Stack & Architectural Constraints

| Layer | Technology | Specification / Version |
|---|---|---|
| **Frontend** | HTML5, CSS3, Modern ES6+ JavaScript | Vanilla JS, Web APIs (MediaPipe Tasks Vision v0.10.21, Geolocation, Web Speech API) |
| **Backend** | Python 3.11+, Flask 3.1.3 | Flask, Flask-CORS, python-dotenv, Werkzeug |
| **Database** | SQLite3 | Relational schema with WAL mode & foreign keys enabled |
| **Integrations** | Telegram Bot API, FCM, Google Maps | Backend-authenticated REST requests |

---

## 4. Non-Functional & Security Constraints
1. **Execution Model**: Strictly browser-side MediaPipe inference for video frames; no high-latency video frame streaming to the backend.
2. **Secret Management**: All API keys, bot tokens, and session secrets stored in `.env` and accessed strictly by backend services.
3. **Data Integrity**: Foreign keys enforced in SQLite; transactions wrapped atomically.
4. **Reliability**: Central SOS dispatch must succeed even if GPS or notification channels partially fail.
