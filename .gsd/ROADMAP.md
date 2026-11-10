---
milestone: SOS Guardian Core Delivery
version: 1.0.0
updated: 2026-11-10T09:42:00+05:30
---

# Roadmap — SOS Guardian

> **Current Phase:** Phase 2 — Core System Stabilization  
> **Status:** Completed Phase 2 (Awaiting User Approval for Phase 3)  
> **Approval Protocol:** Strict phase-by-phase execution control. Do NOT advance without explicit user approval (`APPROVE PHASE [N]`).

---

## Must-Haves (from SPEC.md)

- [x] Multi-modal SOS triggers: Manual, Open-Palm Gesture (browser MediaPipe), Voice commands (Web Speech API - Phase 3).
- [x] 5-second countdown with visual/audio abort on all triggers.
- [x] Robust GPS acquisition with fallback for missing/denied location (Tested & Verified).
- [x] Atomic SQLite emergency event persistence with foreign key constraints (Tested & Verified).
- [ ] Emergency notification dispatch to Telegram Bot API with location maps link and provider status tracking (Phase 4).
- [ ] Secure user authentication and complete user data isolation (Phase 5).

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
**Status:** 🔄 Completed (Awaiting Approval to proceed to Phase 3)  
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
**Status:** ⬜ Not Started (Awaiting Phase 2 Approval)  
**Objective:** Implement hands-free emergency voice recognition using browser Web Speech API for predefined distress commands ("SOS", "Help me", "Emergency") with false-positive protection and continuous error recovery.  
**Depends on:** Phase 2 approval.

---

### Phase 4: Emergency Notification Delivery
**Status:** ⬜ Not Started  
**Objective:** Implement production-ready Telegram Bot API dispatcher, establish modular SMS provider abstraction, verify FCM push notification integration, and build multichannel delivery tracking.  
**Depends on:** Phase 3 approval.

---

### Phase 5: Security Hardening & UI/UX Polish
**Status:** ⬜ Not Started  
**Objective:** Harden authentication (session hygiene, password hashing, route protection, data isolation), polish dashboard interface for mobile-first accessibility, and refine status indicators.  
**Depends on:** Phase 4 approval.

---

### Phase 6: Intelligent Emergency Features
**Status:** ⬜ Not Started  
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
| **Phase 2** | Core System Stabilization | 🔄 Completed (Review) | 100% |
| **Phase 3** | Voice SOS Engine | ⬜ Not Started | 0% |
| **Phase 4** | Emergency Notification Delivery | ⬜ Not Started | 0% |
| **Phase 5** | Security Hardening & UI/UX Polish | ⬜ Not Started | 0% |
| **Phase 6** | Intelligent Emergency Features | ⬜ Not Started | 0% |
| **Phase 7** | Production Deployment & Final Verification | ⬜ Not Started | 0% |
