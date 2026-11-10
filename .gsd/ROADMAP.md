---
milestone: SOS Guardian Core Delivery
version: 1.0.0
updated: 2026-11-10T10:33:00+05:30
---

# Roadmap — SOS Guardian

> **Current Phase:** Phase 5 — Security Hardening & UI/UX Polish  
> **Status:** Completed Phase 5 (Awaiting User Approval for Phase 6)  
> **Approval Protocol:** Strict phase-by-phase execution control. Do NOT advance without explicit user approval (`APPROVE PHASE [N]`).

---

## Must-Haves (from SPEC.md)

- [x] Multi-modal SOS triggers: Manual, Open-Palm Gesture (browser MediaPipe), Voice commands (Web Speech API).
- [x] 5-second countdown with visual/audio abort on all triggers.
- [x] Robust GPS acquisition with fallback for missing/denied location.
- [x] Atomic SQLite emergency event persistence with foreign key constraints.
- [x] Emergency notification dispatch to Telegram Bot API with location maps link and provider status tracking.
- [x] Secure user authentication, session hygiene, rate limiting, and complete cross-user data isolation.
- [x] Real-time System Readiness Matrix reflecting active sensor and contact arming status.
- [x] End-to-end automatic SMS alert integration (Guardian 10-digit mobile input, no-app requirement, Fast2SMS Quick route `route="q"`, clickable Google Maps pin: `https://www.google.com/maps?q=LAT,LONG`).

---

## Phase Breakdown

### Phase 0: Project Setup & Architecture Planning
**Status:** ✅ Complete (Approved)  
**Objective:** Establish workspace structure, extract codebase, initialize repository tracking, define architectural blueprints, formalize `SPEC.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `STATE.md`, and verify planning baseline.

---

### Phase 1: Existing Project Audit & Codebase Health
**Status:** ✅ Complete (Approved)  
**Objective:** In-depth audit of extracted codebase (`backend/app.py`, `backend/database.py`, `backend/gesture_detector.py`, `backend/notifications.py`, `static/app.js`, `templates/index.html`). Catalog syntax errors, architectural misalignments, database schema gaps, and dependency requirements.

---

### Phase 2: Core System Stabilization
**Status:** ✅ Complete (Approved)  
**Objective:** Stabilize Manual SOS, GPS handling, SQLite database event recording, and implement reliable client-side MediaPipe Open-Palm gesture detection with stability and cooldown mechanisms.  
**Deliverables:**
- [x] Fixed backend startup crash: decoupled unused OpenCV/MediaPipe imports from `backend/app.py` line 1.
- [x] Resilient GPS handling: frontend (`static/app.js`) and backend (`backend/app.py`) now support emergency activation without GPS (timeout guard, graceful fallback, location_available flag).
- [x] Database migration: `sos_events` migrated to allow nullable coordinates (`latitude`, `longitude`, `maps_url`), `emergency_contacts` enhanced with `telegram_chat_id`, and `PRAGMA foreign_keys = ON;` enforced.
- [x] Re-engineered client-side MediaPipe HandLandmarker: pinned matching CDN/WASM versions (`@0.10.21`), automatic CPU delegate fallback, robust 5-digit palm geometry algorithm, and 350ms temporal debouncing buffer.
- [x] Created automated test suites: `tests/test_phase2_backend.py` (7 tests passing) and `tests/test_gesture_math.js` (4 tests passing).
- [x] Formatted and generated `PHASE_REPORT.md` for Phase 2.

---

### Phase 3: Voice SOS Engine
**Status:** ✅ Complete (Approved)  
**Objective:** Implement hands-free emergency voice recognition using browser Web Speech API for predefined distress commands ("SOS", "Help me", "Emergency", "I need help", "Save me", "Call for help") with false-positive protection, continuous error recovery, live transcript feedback, and pause/resume controls.  
**Deliverables:**
- [x] Implemented dedicated Voice SOS dashboard panel in `templates/index.html` with status badge, toggle controls, live transcript display, and configured emergency phrase badges.
- [x] Added responsive dark-mode styling in `static/style.css` for voice panel, controls, transcripts, and emergency phrase tags.
- [x] Implemented robust Web Speech API lifecycle management in `static/app.js`: continuous listening, automatic 600ms debounce reconnection on browser silence, and clean `onerror` classification (`not-allowed`, `no-speech`, `network`).
- [x] Built false-positive mitigation using word-boundary regular expressions (`\b(...) \b/i`) preventing unwanted triggers from words containing substrings (e.g., "associated", "asbestos", "season", "espresso", "emerging").
- [x] Connected voice triggers directly to 5-second countdown engine with 15-second post-trigger cooldown buffer and cancellation reset.
- [x] Implemented user-controlled pause and resume (`toggleVoiceSOS`) functionality.
- [x] Authored and executed automated unit test suite (`tests/test_voice_matching.js`): 27/27 test cases passing (14 positive emergency triggers + 13 false-positive rejections).
- [x] Verified zero backend regression via `tests/test_phase2_backend.py` (7/7 tests passing).

---

### Phase 4: Emergency Notification Delivery
**Status:** ✅ Complete (Approved)  
**Objective:** Implement production-ready Telegram Bot API dispatcher, establish modular SMS provider abstraction, verify FCM push notification integration, and build multichannel delivery tracking.  
**Deliverables:**
- [x] Built Telegram Bot API dispatcher (`backend/providers/telegram_provider.py`) supporting HTML emergency alert formatting, location links, explicit mock fallback mode, and Telegram API error classification (400, 401, 429).
- [x] Built provider-independent SMS abstraction (`backend/providers/sms_provider.py`) with `BaseSMSProvider`, `MockSMSProvider`, `TwilioSMSProvider`, `Fast2SMSProvider`, and factory `get_sms_provider()`.
- [x] Created `notification_logs` table in `data/sos_guardian.db` and updated `backend/database.py` with foreign key relations, audit logging (`log_notification`), and history retrieval (`get_notification_logs`).
- [x] Re-architected `backend/notifications.py` into a unified multichannel orchestrator dispatching alerts across all configured channels per contact and computing aggregate delivery status.
- [x] Implemented individual contact test endpoint (`POST /api/contacts/<id>/test`) and UI button (`🧪 Test`) in `static/app.js` and `static/style.css` to verify Telegram and SMS routing without false alarms.
- [x] Enhanced SOS history in `static/app.js` and `backend/database.py` to display channel delivery breakdown badges (`✈️ telegram: sent`, `📱 sms: simulated`) and graceful location handling.
- [x] Created `.env.example` documenting all configuration keys (`TELEGRAM_BOT_TOKEN`, `SMS_PROVIDER`, `TWILIO_*`, `FAST2SMS_*`, `FCM_SERVER_KEY`).
- [x] Authored and executed automated unit test suite `tests/test_notifications.py` (11/11 tests passing) and confirmed zero regressions across all 49 total tests.

---

### Phase 5: Security Hardening & UI/UX Polish (including Automatic SMS Integration)
**Status:** 🔄 Completed (Awaiting Approval to proceed to Phase 6)  
**Objective:** Harden authentication (session hygiene, cookie policies, sliding-window rate limiting, input validation, cross-user isolation), implement real-time System Readiness Matrix (PRD Module B), optimize mobile accessibility, and complete end-to-end automatic SMS dispatch.  
**Deliverables:**
- [x] Implemented thread-safe in-memory sliding window rate limiter (`backend/rate_limiter.py`).
- [x] Configured strict session cookie hygiene: `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `PERMANENT_SESSION_LIFETIME=timedelta(days=7)`, `MAX_CONTENT_LENGTH=2MB`.
- [x] Added security response headers in `backend/app.py`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`.
- [x] Implemented endpoint rate limits: `/api/auth/login` (5/60s), `/api/auth/register` (10/60s), `/api/sos` (1/3s), `/api/contacts/<id>/test` (5/60s).
- [x] Added strict input validation for user registration (email regex, 6-128 char password), contact creation (phone regex, telegram regex, 20 contacts limit), and SOS requests (trigger modality & coordinate range validation).
- [x] Enforced strict cross-user data isolation and route protection on all contact management and SOS endpoints.
- [x] Built dynamic System Readiness Matrix in `templates/index.html`, `static/style.css`, and `static/app.js` with live multi-sensor hardware status (Camera/Gesture, Voice, GPS, Contacts) and overall operational badge.
- [x] Optimized touch target accessibility (44px minimum height/width) and added `aria-label` tags for screen readers.
- [x] Completed End-to-End Automatic SMS Alert Integration:
  - Form allows entering guardian name and 10-digit mobile number, saving directly to SQLite. Recipient requires NO app or registration.
  - Wired Fast2SMS using Quick SMS route (`route="q"`) utilizing free trial signup credits.
  - Added 10-digit phone cleaner for Indian numbers (`clean_phone_number`).
  - Configured `SMS_PROVIDER=mock` as default in `.env` to prevent burning credits during automated testing.
  - Automatically pulls saved numbers from SQLite on SOS activation, generating clickable Google Maps pin: `https://www.google.com/maps?q=LAT,LONG` (or `'GPS Unavailable'`).
- [x] Authored and executed automated security and notification tests (`tests/test_phase5_security.py`, `tests/test_notifications.py`, and `tests/verify_sms_e2e.py`).
- [x] Verified zero regressions across all 66 total automated checks.

---

### Phase 6: Intelligent Emergency Features
**Status:** ⬜ Not Started (Awaiting Phase 5 Approval)  
**Objective:** Explore and prototype advanced intelligent features: fall detection via pose estimation, live location tracking, and multi-contact escalation.  
**Depends on:** Phase 5 approval.

---

### Phase 7: Production Deployment & Final Verification
**Status:** ⬜ Not Started  
**Objective:** Prepare deployment configuration (Gunicorn, Render, environment variables, HTTPS/WSS), execute end-to-end integration tests, and finalize release.  
**Depends on:** Phase 6 approval.

---

## Progress Summary

| Phase | Description | Status | Complete |
|---|---|---|---|
| **Phase 0** | Project Setup & Architecture Planning | ✅ Complete | 100% |
| **Phase 1** | Existing Project Audit & Codebase Health | ✅ Complete | 100% |
| **Phase 2** | Core System Stabilization | ✅ Complete | 100% |
| **Phase 3** | Voice SOS Engine | ✅ Complete | 100% |
| **Phase 4** | Emergency Notification Delivery | ✅ Complete | 100% |
| **Phase 5** | Security Hardening, UI/UX & Live SMS | 🔄 Completed (Review) | 100% |
| **Phase 6** | Intelligent Emergency Features | ⬜ Not Started | 0% |
| **Phase 7** | Production Deployment & Final Verification | ⬜ Not Started | 0% |
