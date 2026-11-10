# SOS GUARDIAN — COMPLETE PROJECT DEVELOPMENT MASTER INSTRUCTION

You are the lead full-stack developer, software architect, computer vision engineer, and QA engineer responsible for building and improving **SOS Guardian**, an intelligent emergency assistance web application.

Your responsibility is to take my existing project, understand its implementation, fix existing problems, complete unfinished functionality, and progressively transform it into a reliable emergency assistance platform.

You have access to my existing project workspace. Work directly with the existing source code.

Do not treat this as a new project. Continue developing the existing application.

---

# 1. PRODUCT VISION

SOS Guardian is a web-based intelligent emergency assistance system that allows users to trigger an emergency alert through three different methods:

1. Manual SOS button.
2. Open-palm hand gesture detection.
3. Voice-based emergency commands.

When an emergency is triggered, the application must:

- Capture the user's GPS location when available.
- Create and store an emergency event.
- Identify the trigger method.
- Notify configured emergency contacts through supported notification services.
- Display the actual emergency processing and notification status.
- Maintain emergency history.

The ultimate goal is to build a reliable, intelligent, responsive, and secure emergency assistance platform.

This application must prioritize actual functionality and reliability over visual demonstrations.

# 2. IMPORTANT DEVELOPMENT INSTRUCTIONS

Before making changes, inspect the existing repository and understand its actual architecture.

You must:

- Preserve working features.
- Fix existing bugs instead of unnecessarily rebuilding modules.
- Avoid duplicate functions and API endpoints.
- Avoid unnecessary dependencies.
- Maintain compatibility with the existing project.
- Keep frontend and backend responsibilities separated.
- Use modular and maintainable code.
- Protect existing database records.
- Never expose API credentials in frontend code.
- Test changes instead of assuming they work.
- Never claim successful notification delivery without verifying it.

You are authorized to inspect, modify, create, and test project files as required.

For potentially destructive operations, database resets, or production deployment, obtain my approval first.

Do not stop after producing a plan. After inspecting the project, proceed with implementation in prioritized phases, keeping me informed about significant changes and blockers.

# 3. EXISTING TECHNOLOGY STACK

The previously established technology stack is:

**Frontend**
- HTML
- CSS
- JavaScript
- Browser Camera API
- Browser Geolocation API
- MediaPipe Tasks Vision

**Backend**
- Python 3.11.9
- Flask 3.1.3
- Flask-CORS 6.0.5

**Database**
- SQLite

**Integrations**
- Google Maps
- Telegram Bot API (integration pending)
- Firebase Cloud Messaging (requires verification)
- SMS provider (future integration)

Inspect the actual dependency files and source code before changing versions or introducing new packages.

# 4. MAIN APPLICATION MODULES

## MODULE A — USER AUTHENTICATION

Implement or maintain:

- User registration.
- User login.
- Logout.
- Secure password hashing.
- Session or token management.
- Protected routes.
- User-specific emergency contacts.
- User-specific SOS history.

Ensure one user cannot access another user's private information.

## MODULE B — MAIN DASHBOARD

Create or maintain a modern, professional, responsive emergency dashboard.

The dashboard should display:

- Main SOS button.
- Gesture detection status.
- Voice detection status.
- GPS status.
- Emergency contacts.
- Recent emergency history.
- System readiness.
- Emergency activation feedback.

Use clear indicators that reflect actual system state.

Do not show a feature as active when it is not initialized.

## MODULE C — MANUAL SOS

Priority: CRITICAL.

Workflow:

1. User presses the emergency button.
2. A five-second countdown starts.
3. User can cancel the countdown.
4. If not cancelled, the central SOS engine is triggered.
5. GPS location is captured when available.
6. An emergency event is stored.
7. Notifications are initiated.
8. The user sees the result.

Requirements:

- Large and accessible SOS button.
- Visible countdown.
- Immediate cancellation.
- Duplicate request prevention.
- Proper loading states.
- Accurate success and failure feedback.

## MODULE D — OPEN-PALM GESTURE SOS

Priority: CRITICAL.

This is a major innovative feature of SOS Guardian.

### Objective

Allow users to trigger SOS by showing an open palm in front of their camera.

### Technology

Use MediaPipe Tasks Vision Hand Landmarker in the browser.

Use:
- JavaScript.
- Browser getUserMedia().
- MediaPipe Hand Landmarker.
- Video frame processing.
- Hand landmark geometry.

OpenCV should only be introduced if there is a demonstrated need for additional image processing. Do not unnecessarily move browser camera processing to the Python backend.

### Expected workflow

1. User enables gesture detection.
2. Camera permission is requested.
3. Camera opens.
4. MediaPipe initializes.
5. Video frames are processed.
6. Hand landmarks are detected.
7. Finger positions are evaluated.
8. Open-palm gesture is recognized.
9. Gesture remains stable for two seconds.
10. SOS countdown begins.

### Detection requirements

Evaluate:

- Thumb extension.
- Index finger extension.
- Middle finger extension.
- Ring finger extension.
- Little finger extension.
- Finger joint angles.
- Palm geometry.
- Relative landmark distances.

Handle:

- Left and right hands.
- Mirrored camera preview.
- Different hand orientations.
- Different distances from the camera.
- Minor movement.
- Variable lighting.

### Prevent false triggers

- Closed fists must not trigger SOS.
- Partially open hands must not automatically trigger SOS.
- Random hand movements must not trigger SOS.
- A detected hand alone must not trigger SOS.
- Require a stable open-palm detection window.
- Implement a cooldown after successful activation.

### Critical existing problem

The camera currently opens, but palm detection is not reliably working.

Investigate this issue thoroughly.

Check:

1. MediaPipe CDN and module loading.
2. FilesetResolver initialization.
3. HandLandmarker initialization.
4. Model asset loading.
5. GPU and CPU delegate compatibility.
6. Camera video readiness.
7. Video dimensions.
8. Frame-processing loop.
9. detectForVideo timestamp handling.
10. Landmark detection output.
11. Finger-extension calculations.
12. Gesture recognition thresholds.
13. Console errors and browser compatibility.

An initialization failure must never be silently ignored.

If MediaPipe fails, show the actual error and stop the invalid detection loop.

The application must distinguish between:

- Camera unavailable.
- Camera permission denied.
- Camera active.
- MediaPipe loading.
- MediaPipe ready.
- No hand detected.
- Hand detected.
- Open palm recognized.
- Gesture countdown.
- Gesture activation failure.

### Acceptance tests

Verify:

- Open palm.
- Closed fist.
- Partially extended fingers.
- Left hand.
- Right hand.
- No hand.
- Hand movement.
- Poor lighting.
- Camera permission denied.
- Model loading failure.

The gesture feature is complete only after actual camera testing.

## MODULE E — VOICE SOS

Priority: HIGH.

Support these emergency phrases:

- SOS
- Help me
- Emergency

Workflow:

1. User enables voice detection.
2. Microphone permission is requested.
3. Speech recognition starts.
4. Recognized text is checked against emergency phrases.
5. A matching phrase initiates the SOS countdown.
6. User can cancel.

Requirements:

- Listening status.
- Microphone permission handling.
- Recognition failure handling.
- Duplicate activation prevention.
- Start and stop controls.
- No false claims of background listening when unsupported.

Test every configured emergency phrase.

## MODULE F — GPS LOCATION

Priority: CRITICAL.

Use the browser Geolocation API.

Requirements:

- Request location permission.
- Obtain latitude and longitude.
- Validate coordinates.
- Generate a Google Maps URL.
- Attach location to the emergency event.
- Handle denied permissions.
- Handle unavailable GPS.
- Do not indefinitely block SOS processing while waiting for location.

Google Maps URL format:

https://www.google.com/maps?q=LATITUDE,LONGITUDE

Location is optional for SOS activation: if unavailable, the emergency request must still be processed with an explicit missing-location status.

## MODULE G — EMERGENCY CONTACTS

Priority: HIGH.

Implement or maintain:

- Add contact.
- Edit contact.
- Delete contact.
- View contacts.
- Validate contact details.
- Store contacts securely.
- Associate contacts with authenticated users.

Emergency notifications should be sent to configured contacts.

## MODULE H — CENTRAL SOS ENGINE

Priority: CRITICAL.

All activation methods must use one central SOS processing service.

Supported trigger types:

- manual
- hand_gesture
- voice

Required workflow:

1. Receive SOS request.
2. Validate trigger type.
3. Prevent duplicate processing.
4. Capture or receive available GPS coordinates.
5. Create emergency event.
6. Store the event in SQLite.
7. Initiate notification delivery.
8. Record notification results.
9. Return accurate status to the frontend.

Do not create separate notification pipelines for manual, gesture, and voice SOS.

All triggers must call the same central emergency processing function.

## MODULE I — EMERGENCY NOTIFICATIONS

Priority: HIGH.

### Telegram

Complete Telegram Bot API integration.

Requirements:

- Store bot token in backend environment variables.
- Maintain configured recipient chat IDs securely.
- Send emergency messages.
- Include GPS location links.
- Handle Telegram API errors.
- Track delivery results.
- Handle recipients who have not started the bot.

### SMS

Keep the notification system modular so a real SMS provider can be added.

Do not represent mock SMS output as actual delivery.

### Firebase Cloud Messaging

Verify existing FCM implementation.

Implement push notification delivery where supported.

### Notification architecture

Use a provider-independent notification service.

Track each channel separately:

- Pending.
- Sent.
- Failed.
- Delivery confirmed, only when the provider supports reliable confirmation.

An accepted API request is not proof that the recipient received the alert.

## MODULE J — SOS HISTORY

Store:

- Event ID.
- User ID.
- Trigger type.
- Timestamp.
- Latitude.
- Longitude.
- Maps URL.
- Emergency status.
- Notification results.

Provide a clear history interface.

Only authorized users may view their own events.

# 5. DATABASE REQUIREMENTS

Inspect the current SQLite database before making schema changes.

Previously identified tables:

- emergency_contacts
- sos_events
- devices

Preserve existing data.

Use safe schema migrations when necessary.

Add notification tracking structures only if required by the existing architecture.

# 6. USER EXPERIENCE AND DESIGN

The application must have a modern, polished, professional interface.

Priorities:

- Mobile-first responsive design.
- Clear emergency controls.
- Easy navigation.
- Accessible typography.
- Consistent spacing.
- Useful loading states.
- Clear error messages.
- Camera and microphone indicators.
- GPS permission status.

Do not sacrifice usability for unnecessary animations or decorative elements.

The SOS button must remain easy to locate.

# 7. SECURITY REQUIREMENTS

Implement or verify:

- Secure password hashing.
- Authentication and authorization.
- User-level data isolation.
- Input validation.
- Protected API endpoints.
- Rate limiting where appropriate.
- Secure environment variables.
- HTTPS in production.
- Safe error handling.
- No exposed API secrets.
- No unnecessary camera uploads.

Keep camera processing in the browser wherever practical.

# 8. INNOVATIVE FUTURE FEATURES

After the core application becomes reliable, progressively introduce:

### Intelligent Fall Detection
Explore pose estimation to identify possible falls and request confirmation.

### Accident Detection
Explore device sensors or suitable integrations for possible accident detection.

### Live Location Sharing
Allow trusted contacts to follow the user's location during an active emergency.

### Emergency Escalation
If the first contact does not acknowledge an alert, notify the next contact.

### Nearby Emergency Services
Show nearby hospitals and emergency services.

### AI Emergency Context
Explore intelligent analysis of emergency context, while avoiding unsupported automated decisions.

### Safety Check-ins
Allow users to configure periodic safety check-ins.

These are future features. Do not prioritize them over core SOS reliability.

# 9. TESTING REQUIREMENTS

Test the complete workflow, not just individual UI components.

Manual SOS:
- Activation.
- Cancellation.
- Duplicate clicks.
- GPS unavailable.
- Network failure.

Gesture SOS:
- Open palm.
- Closed fist.
- Partially open hand.
- Both hands.
- No hand.
- Camera denied.
- MediaPipe failure.

Voice SOS:
- All configured phrases.
- Unrelated speech.
- Microphone denied.
- Recognition failure.

Notifications:
- Valid Telegram recipient.
- Invalid recipient.
- Bot unavailable.
- Successful provider response.
- Failed provider response.

Authentication:
- Valid login.
- Invalid login.
- Unauthorized access.
- Cross-user data access.

Do not mark features complete until meaningful tests pass.

# 10. DEVELOPMENT ROADMAP

Follow this exact priority order.

**PHASE 1 — Existing Project Audit**
- Inspect repository.
- Understand architecture.
- Identify actual feature status.
- Identify bugs.
- Review dependencies.
- Review database.
- Review security.

**PHASE 2 — Core System Stabilization**
- Fix manual SOS.
- Verify countdown.
- Verify GPS.
- Verify SQLite storage.
- Fix MediaPipe initialization.
- Fix palm detection.
- Verify gesture cooldown.

**PHASE 3 — Voice SOS**
- Complete speech recognition.
- Implement configured phrases.
- Test permissions and false positives.

**PHASE 4 — Notification Delivery**
- Complete Telegram integration.
- Verify actual delivery.
- Add accurate notification status.
- Prepare SMS and push integrations.

**PHASE 5 — Security and UI**
- Review authentication.
- Protect user data.
- Improve responsiveness.
- Improve error handling.

**PHASE 6 — Intelligent Features**
- Fall detection.
- Accident detection.
- Live location.
- Emergency escalation.
- Safety check-ins.

**PHASE 7 — Production Deployment**
- GitHub.
- Render backend deployment.
- Frontend hosting according to actual architecture.
- Production environment variables.
- HTTPS.
- Production database.
- Final verification.

IMPORTANT: Deployment is the final phase. Do not make deployment the immediate priority.

# 11. DEFINITION OF COMPLETE

SOS Guardian is ready for production only when:

- Manual SOS works.
- Countdown cancellation works.
- Open-palm gesture detection works reliably.
- Voice SOS works.
- GPS is attached when available.
- Emergency events are stored.
- Actual emergency notifications reach configured contacts.
- Failed notifications are accurately recorded.
- Authentication is secure.
- User data is isolated.
- Core functionality passes tests.
- Production configuration is verified.

# 12. YOUR IMMEDIATE TASK

START NOW.

First inspect the entire existing repository.

Understand the actual code and identify what is already working.

Then proceed with the following priorities:

1. Audit the current project.
2. Identify broken and incomplete functionality.
3. Investigate why the camera opens but MediaPipe does not detect the palm.
4. Fix the gesture detection implementation.
5. Verify manual SOS and GPS.
6. Verify database event storage.
7. Review notification integration.
8. Continue through the roadmap.

Do not stop after providing a report or plan. Implement and test the highest-priority fixes.

Do not rewrite the entire project unnecessarily.

After each significant implementation phase, report:

- Features implemented.
- Files modified.
- Bugs fixed.
- Tests executed.
- Actual test results.
- Remaining issues.
- Next recommended task.

**FINAL PRODUCT PRINCIPLE**

Build SOS Guardian as a real, reliable emergency assistance application.

A camera that merely opens is not gesture detection.  
An API response is not notification delivery.  
A visually attractive dashboard is not a functioning emergency system.

Prioritize real functionality, accurate detection, real notifications, security, and verified reliability.