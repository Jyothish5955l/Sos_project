---
milestone: SOS Guardian Core Delivery
version: 1.0.0
updated: 2026-11-10T09:30:00+05:30
---

# Roadmap — SOS Guardian

> **Current Phase:** Phase 1 — Existing Project Audit & Codebase Health  
> **Status:** Completed Phase 1 Audit (Awaiting User Approval for Phase 2)  
> **Approval Protocol:** Strict phase-by-phase execution control. Do NOT advance without explicit user approval (`APPROVE PHASE [N]`).

---

## Must-Haves (from SPEC.md)

- [ ] Multi-modal SOS triggers: Manual, Open-Palm Gesture (browser MediaPipe), Voice commands (Web Speech API).
- [ ] 5-second countdown with visual/audio abort on all triggers.
- [ ] Robust GPS acquisition with fallback for missing/denied location.
- [ ] Atomic SQLite emergency event persistence with foreign key constraints.
- [ ] Emergency notification dispatch to Telegram Bot API with location maps link and provider status tracking.
- [ ] Secure user authentication and complete user data isolation.

---

## Phase Breakdown

### Phase 0: Project Setup & Architecture Planning
**Status:** ✅ Complete (Approved)  
**Objective:** Establish workspace structure, extract codebase, initialize repository tracking, define architectural blueprints, formalize `SPEC.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `STATE.md`, and verify planning baseline.

---

### Phase 1: Existing Project Audit & Codebase Health
**Status:** 🔄 Completed (Awaiting Approval to proceed to Phase 2)  
**Objective:** In-depth audit of extracted codebase (`backend/app.py`, `backend/database.py`, `backend/gesture_detector.py`, `backend/notifications.py`, `static/app.js`, `templates/index.html`). Catalog syntax errors, architectural misalignments (e.g. server-side vs client-side gesture detection), database schema gaps, dependency requirements, and test baseline.  
**Deliverables:**
- [x] Static analysis and syntax audit across Python backend and JS frontend.
- [x] Identified fatal import crash in `backend/app.py` (`from gesture_detector import detect_hand` -> missing `cv2`/`mediapipe`/`numpy`).
- [x] Audited database schema, migration handling, foreign keys, and `NOT NULL` coordinate constraints.
- [x] Audited MediaPipe loading in `static/app.js`: discovered version mismatch (`0.10.21` bundle vs `0.10.22` wasm), missing GPU-to-CPU fallback, and brittle palm stability logic.
- [x] Audited GPS and Manual SOS flow: discovered hard abort in both frontend and backend when coordinates are unavailable.
- [x] Audited notification services: discovered missing Telegram integration, empty SMS provider, and non-functional FCM stub.
- [x] Audited security: hardcoded secret key, orphaned database records, and open CORS.
- [x] Compiled Phase 1 audit report in `PHASE_REPORT.md`.

---

### Phase 2: Core System Stabilization
**Status:** ⬜ Not Started (Awaiting Phase 1 Approval)  
**Objective:** Stabilize Manual SOS, GPS handling, SQLite database event recording, and implement reliable client-side MediaPipe Open-Palm gesture detection with stability and cooldown mechanisms.  
**Depends on:** Phase 1 approval.  
**Planned Tasks:**
- Task 2.1: Fix backend startup (decouple unused `gesture_detector.py` from `app.py`).
- Task 2.2: Make GPS coordinate payload resilient in frontend (`static/app.js`) and backend (`backend/app.py`), allowing emergency activation without coordinates.
- Task 2.3: Migrate SQLite database schema to allow nullable `latitude`, `longitude`, `maps_url` in `sos_events` and add `telegram_chat_id` in `emergency_contacts`.
- Task 2.4: Fix client-side MediaPipe HandLandmarker initialization: align CDN and WASM versions (`0.10.21`), add CPU delegate fallback, improve palm geometry detection, and implement a temporal smoothing buffer (debounce) for the 2-second stability hold.
- Task 2.5: Automated & manual test verification of manual SOS and gesture detection.

---

### Phase 3: Voice SOS Engine
**Status:** ⬜ Not Started  
**Objective:** Implement hands-free emergency voice recognition using browser Web Speech API for predefined distress commands ("SOS", "Help me", "Emergency") with false-positive protection.  
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
| **Phase 1** | Existing Project Audit & Codebase Health | 🔄 Completed (Review) | 100% |
| **Phase 2** | Core System Stabilization | ⬜ Not Started | 0% |
| **Phase 3** | Voice SOS Engine | ⬜ Not Started | 0% |
| **Phase 4** | Emergency Notification Delivery | ⬜ Not Started | 0% |
| **Phase 5** | Security Hardening & UI/UX Polish | ⬜ Not Started | 0% |
| **Phase 6** | Intelligent Emergency Features | ⬜ Not Started | 0% |
| **Phase 7** | Production Deployment & Final Verification | ⬜ Not Started | 0% |
