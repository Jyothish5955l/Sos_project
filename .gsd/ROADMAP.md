---
milestone: SOS Guardian Core Delivery
version: 1.0.0
updated: 2026-11-10T09:15:00+05:30
---

# Roadmap — SOS Guardian

> **Current Phase:** Phase 0 — Project Setup & Architecture Planning  
> **Status:** Executing / Completing Phase 0  
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
**Status:** 🔄 In Progress (Closing)  
**Objective:** Establish workspace structure, extract codebase, initialize repository tracking, define architectural blueprints, formalize `SPEC.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `STATE.md`, and verify planning baseline.  
**Deliverables:**
- [x] Extract legacy codebase from archive into active workspace.
- [x] Configure standard `.gitignore`.
- [x] Initialize Git version control.
- [x] Formalize `.gsd/SPEC.md` and `.gsd/ARCHITECTURE.md`.
- [x] Establish phased execution plan in `.gsd/ROADMAP.md`.
- [x] Initialize `.gsd/STATE.md`.
- [x] Generate `PHASE_REPORT.md` and await approval.

---

### Phase 1: Existing Project Audit & Codebase Health
**Status:** ⬜ Not Started (Awaiting Phase 0 Approval)  
**Objective:** In-depth audit of extracted codebase (`backend/app.py`, `backend/database.py`, `backend/gesture_detector.py`, `backend/notifications.py`, `static/app.js`, `templates/index.html`). Catalog syntax errors, architectural misalignments (e.g. server-side vs client-side gesture detection), database schema gaps, dependency requirements, and test baseline.  
**Depends on:** Phase 0 approval.  
**Planned Tasks:**
- Task 1.1: Static analysis and syntax audit across Python backend and JS frontend.
- Task 1.2: Audit database schema, migration handling, and foreign key integrity.
- Task 1.3: Audit MediaPipe loading, CDN assets, and client-side vs backend gesture implementation.
- Task 1.4: Catalog bugs, security vulnerabilities, and dead/redundant code.
- Task 1.5: Compile Phase 1 audit report.

---

### Phase 2: Core System Stabilization
**Status:** ⬜ Not Started  
**Objective:** Stabilize Manual SOS, GPS handling, SQLite database event recording, and implement reliable client-side MediaPipe Open-Palm gesture detection with stability and cooldown mechanisms.  
**Depends on:** Phase 1 approval.  
**Planned Tasks:**
- Task 2.1: Fix manual SOS countdown and instant abort logic in frontend.
- Task 2.2: Make GPS coordinate payload resilient (allow emergency creation even when GPS is missing/denied).
- Task 2.3: Fix SQLite database event creation and retrieval functions.
- Task 2.4: Implement client-side MediaPipe HandLandmarker open-palm detection algorithm with 2-second stability window and cooldown.
- Task 2.5: Automated & manual test verification of manual SOS and gesture detection.

---

### Phase 3: Voice SOS Engine
**Status:** ⬜ Not Started  
**Objective:** Implement hands-free emergency voice recognition using browser Web Speech API for predefined distress commands ("SOS", "Help me", "Emergency") with false-positive protection.  
**Depends on:** Phase 2 approval.  
**Planned Tasks:**
- Task 3.1: Implement Web Speech API lifecycle management (start, stop, auto-restart, error handling).
- Task 3.2: Implement keyword matching and fuzzy tolerance for distress phrases.
- Task 3.3: Connect voice trigger to unified 5-second countdown engine.
- Task 3.4: Automated & manual tests across phrases and noisy input.

---

### Phase 4: Emergency Notification Delivery
**Status:** ⬜ Not Started  
**Objective:** Implement production-ready Telegram Bot API dispatcher, establish modular SMS provider abstraction, verify FCM push notification integration, and build multichannel delivery tracking.  
**Depends on:** Phase 3 approval.  
**Planned Tasks:**
- Task 4.1: Implement Telegram Bot API notification service with location maps link and error recovery.
- Task 4.2: Build pluggable SMS provider interface with clear mock/live indicators.
- Task 4.3: Implement FCM push notification handler and service worker integration.
- Task 4.4: Record granular per-channel delivery statuses (`Pending`, `Sent`, `Failed`, `Confirmed`) in SQLite.

---

### Phase 5: Security Hardening & UI/UX Polish
**Status:** ⬜ Not Started  
**Objective:** Harden authentication (session hygiene, password hashing, route protection, data isolation), polish dashboard interface for mobile-first accessibility, and refine status indicators.  
**Depends on:** Phase 4 approval.  
**Planned Tasks:**
- Task 5.1: Review and harden authentication endpoints, session cookies, and route guards.
- Task 5.2: Enforce strict user data isolation on contacts, permissions, and SOS history.
- Task 5.3: Enhance responsive dashboard UI, typography, status badges, and feedback modals.
- Task 5.4: Comprehensive security audit and penetration test simulation.

---

### Phase 6: Intelligent Emergency Features
**Status:** ⬜ Not Started  
**Objective:** Explore and prototype advanced intelligent features: fall detection via pose estimation, live location tracking, and multi-contact escalation.  
**Depends on:** Phase 5 approval.  
**Planned Tasks:**
- Task 6.1: Fall detection prototype evaluation using MediaPipe Pose.
- Task 6.2: Live location sharing link generation and tracking session model.
- Task 6.3: Emergency escalation protocol across configured contact priority hierarchy.

---

### Phase 7: Production Deployment & Final Verification
**Status:** ⬜ Not Started  
**Objective:** Prepare deployment configuration (Gunicorn, Render, environment variables, HTTPS/WSS), execute end-to-end integration tests, and finalize release.  
**Depends on:** Phase 6 approval.  
**Planned Tasks:**
- Task 7.1: Configure production WSGI runner (`gunicorn`) and deployment configuration files.
- Task 7.2: Verify production environment variables and HTTPS asset delivery.
- Task 7.3: Full end-to-end multi-modal emergency activation drill and final verification.

---

## Progress Summary

| Phase | Description | Status | Complete |
|---|---|---|---|
| **Phase 0** | Project Setup & Architecture Planning | 🔄 In Progress | 95% |
| **Phase 1** | Existing Project Audit & Codebase Health | ⬜ Not Started | 0% |
| **Phase 2** | Core System Stabilization | ⬜ Not Started | 0% |
| **Phase 3** | Voice SOS Engine | ⬜ Not Started | 0% |
| **Phase 4** | Emergency Notification Delivery | ⬜ Not Started | 0% |
| **Phase 5** | Security Hardening & UI/UX Polish | ⬜ Not Started | 0% |
| **Phase 6** | Intelligent Emergency Features | ⬜ Not Started | 0% |
| **Phase 7** | Production Deployment & Final Verification | ⬜ Not Started | 0% |
