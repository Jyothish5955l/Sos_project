# ARCHITECTURE.md — SOS Guardian System Architecture

> **Milestone**: Core Delivery 1.0.0  
> **Status**: APPROVED ARCHITECTURE BASELINE (Phase 0)  
> **Last Updated**: 2026-11-10

---

## 1. System Topology Overview

SOS Guardian is engineered as an emergency-first, low-latency assistance web application. It combines client-side sensory inputs (vision, speech, location, user interaction) with a centralized Flask/SQLite backend engine that orchestrates multi-channel notifications.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (BROWSER)                              │
│                                                                        │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│   │   Manual Button  │  │  MediaPipe Vision│  │  Web Speech API  │    │
│   │  (5s Countdown)  │  │ (Open-Palm Model)│  │ (Distress Words) │    │
│   └─────────┬────────┘  └────────┬─────────┘  └────────┬─────────┘    │
│             │                    │                     │               │
│             └────────────────────┼─────────────────────┘               │
│                                  ▼                                     │
│                     ┌───────────────────────────┐                      │
│                     │ Browser Geolocation API   │                      │
│                     │  (Latitude, Longitude)    │                      │
│                     └────────────┬──────────────┘                      │
│                                  │                                     │
│                                  │ JSON POST /api/sos                  │
└──────────────────────────────────┼─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FLASK BACKEND ENGINE                            │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Central SOS Route & Event Dispatcher (`/api/sos`)              │   │
│   │ - Input Sanitization & Coordinate Validation                   │   │
│   │ - Session & Auth Verification (`login_required`)               │   │
│   │ - Deduplication & Rapid Re-trigger Guard                       │   │
│   └──────────────────────┬──────────────────┬──────────────────────┘   │
│                          │                  │                          │
│                          ▼                  ▼                          │
│   ┌───────────────────────────┐        ┌───────────────────────────┐   │
│   │ SQLite Storage Engine     │        │ Notification Dispatcher   │   │
│   │ - `users`                 │        │ - Telegram Bot API        │   │
│   │ - `emergency_contacts`    │        │ - SMS Provider (Modular)  │   │
│   │ - `sos_events`            │        │ - Push / FCM Service      │   │
│   └───────────────────────────┘        └─────────────┬─────────────┘   │
└──────────────────────────────────────────────────────┼─────────────────┘
                                                       │
                                                       ▼
                                         ┌───────────────────────────┐
                                         │  External Notification    │
                                         │  Channels & Recipients    │
                                         └───────────────────────────┘
```

---

## 2. Core System Components

### 2.1 Client-Side Sensor & Detection Layer (`static/app.js`, `templates/index.html`)
- **Manual Trigger**: Primary high-visibility button initiating a 5-second countdown modal with an immediate visual and functional cancel option.
- **Computer Vision Trigger**: Uses `@mediapipe/tasks-vision` (`HandLandmarker`) running completely inside client browser memory via WebGL/Wasm. Evaluates joint angles, fingertip distances relative to wrist, and thumb abduction to detect an open palm. Implements a 2-second stability timer and a post-activation cooldown.
- **Voice Trigger**: Continuous speech listening via `webkitSpeechRecognition` / `SpeechRecognition` configured for target distress phrases ("SOS", "Help me", "Emergency"). Triggers countdown upon match.
- **Geolocation Adapter**: Interrogates `navigator.geolocation.getCurrentPosition`. Captures high-accuracy coordinates with graceful fallback: if permission denied or GPS unavailable, the SOS request proceeds with coordinate nullability indicated.

### 2.2 Application Backend Server (`backend/app.py`)
- **Technology**: Python 3.11+, Flask 3.1.3, Flask-CORS.
- **Authentication**: Session cookie authentication backed by Werkzeug hashed passwords (`generate_password_hash`, `check_password_hash`).
- **Authorization Guard**: Decorator `@login_required` enforcing user boundaries.
- **Central SOS Endpoint**: `/api/sos` accepts `{ latitude, longitude, trigger_type }`. Coordinates are sanitized; if missing/invalid, default fallback handles the dispatch without throwing 400 rejection errors.

### 2.3 Data Persistence Layer (`backend/database.py`, `data/sos_guardian.db`)
- **Technology**: SQLite3 with `Row` factory and foreign key support.
- **Primary Entities**:
  - `users`: User identity, credentials, permission flags, registration timestamp.
  - `emergency_contacts`: User-scoped emergency contacts (name, phone, created_at, user_id).
  - `sos_events`: User-scoped SOS events (latitude, longitude, maps_url, trigger_type, status, created_at, user_id).

### 2.4 Multi-Channel Notification Dispatcher (`backend/notifications.py`, `backend/providers/`)
- **Telegram Bot API**: Backend client making direct HTTPS calls to `https://api.telegram.org/bot<TOKEN>/sendMessage`. Delivers dynamic distress templates including Google Maps URL.
- **SMS Provider**: Abstract interface defining `send_sms(phone, message)` allowing pluggable Twilio / AWS SNS / MessageBird adapters without modifying application logic.
- **FCM Provider**: Firebase Cloud Messaging service worker interface for mobile and desktop browser push alerts.

---

## 3. Data Flow Specification: Emergency Activation

1. **Trigger Recognition**:
   - User clicks Manual SOS, OR
   - MediaPipe detects stable open palm for 2.0s, OR
   - Web Speech API detects emergency phrase.
2. **Countdown & Abort Window**:
   - UI presents a modal countdown from 5 to 0 with acoustic and visual tick indicators.
   - User can click "Cancel SOS" at any time to abort the event before dispatch.
3. **Payload Construction**:
   - Frontend captures available GPS coordinates (`lat`, `lng`).
   - Frontend sends POST to `/api/sos` with `{ latitude, longitude, trigger_type }`.
4. **Backend Processing**:
   - Validates session and user identity.
   - Saves record in `sos_events` table with `status = 'ACTIVE'`.
   - Fetches active contacts for `user_id` from `emergency_contacts`.
5. **Notification Fan-Out**:
   - Asynchronously or iteratively dispatches emergency messages to configured contacts via Telegram and SMS.
   - Updates event status with delivery logs.
6. **Telemetry & History**:
   - Returns JSON response to frontend with event details and delivery report.
   - Frontend transitions to active emergency telemetry screen.

---

## 4. Key Architectural Decisions & Invariants

1. **Browser-Side vs Server-Side Vision**:
   - *Decision*: Hand landmark and palm detection MUST execute purely inside the browser (`static/app.js`).
   - *Rationale*: Streaming raw video frames to `/api/gesture/detect` induces severe network latency, overwhelms server bandwidth, and creates major privacy/security exposure. Server-side OpenCV scripts (`gesture_detector.py`) remain legacy or optional offline test utilities.
2. **Resilient Geolocation**:
   - *Decision*: GPS coordinates are an enrichment, NOT a hard dependency for triggering SOS.
   - *Rationale*: A user in a basement or with GPS turned off must still be able to trigger life-saving notifications.
3. **Single Ingestion Pipeline**:
   - *Decision*: All triggers (manual, gesture, voice) converge onto a single `/api/sos` route and backend event handler.
   - *Rationale*: Eliminates code duplication, guarantees identical notification logic, and simplifies auditability.
