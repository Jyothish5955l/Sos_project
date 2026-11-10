import {
    HandLandmarker,
    FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs";

window.HandLandmarker = HandLandmarker;
window.FilesetResolver = FilesetResolver;


/* ============================================================
   GLOBAL STATE
   ============================================================ */

let currentUser = null;

let countdownTimer = null;
let countdownValue = 5;

let handLandmarker = null;
let cameraStream = null;

let lastVideoTime = -1;

let palmStartTime = null;
let palmLastSeenTime = null;
let lastDetectionTimestamp = 0;

let gestureSosTriggered = false;

let gestureCooldownUntil = 0;


/* ============================================================
   VOICE STATE
   ============================================================ */

let voiceRecognition = null;
let voiceRunning = false;
let voiceTriggered = false;
let voiceEnabled = true;
let voiceCooldownUntil = 0;


/* ============================================================
   SYSTEM READINESS MATRIX STATE
   ============================================================ */

const systemReadiness = {
    gesture: "waiting",
    voice: "waiting",
    gps: "checking",
    contactsCount: 0
};

function updateReadinessUI() {
    const badge = document.getElementById("overallReadinessBadge");
    const gEl = document.getElementById("matrixGestureStatus");
    const vEl = document.getElementById("matrixVoiceStatus");
    const gpsEl = document.getElementById("matrixGpsStatus");
    const cEl = document.getElementById("matrixContactsStatus");

    if (gEl) {
        if (systemReadiness.gesture === "active") {
            gEl.textContent = "🟢 Camera & Palm Active";
            gEl.className = "readiness-value active";
        } else if (systemReadiness.gesture === "waiting") {
            gEl.textContent = "🟡 Initializing Camera...";
            gEl.className = "readiness-value waiting";
        } else {
            gEl.textContent = "🔴 Camera Inactive";
            gEl.className = "readiness-value disabled";
        }
    }

    if (vEl) {
        if (systemReadiness.voice === "listening") {
            vEl.textContent = "🟢 Continuous Listening";
            vEl.className = "readiness-value active";
        } else if (systemReadiness.voice === "paused") {
            vEl.textContent = "🟡 Recognition Paused";
            vEl.className = "readiness-value paused";
        } else if (systemReadiness.voice === "waiting") {
            vEl.textContent = "🟡 Starting Mic...";
            vEl.className = "readiness-value waiting";
        } else {
            vEl.textContent = "🔴 Mic Disabled/Blocked";
            vEl.className = "readiness-value disabled";
        }
    }

    if (gpsEl) {
        if (systemReadiness.gps === "ready") {
            gpsEl.textContent = "🟢 Location Fix Acquired";
            gpsEl.className = "readiness-value ready";
        } else if (systemReadiness.gps === "checking") {
            gpsEl.textContent = "🟡 Acquiring GPS...";
            gpsEl.className = "readiness-value checking";
        } else {
            gpsEl.textContent = "⚠️ Fallback (GPS Denied)";
            gpsEl.className = "readiness-value unavailable";
        }
    }

    if (cEl) {
        if (systemReadiness.contactsCount > 0) {
            cEl.textContent = `🟢 ${systemReadiness.contactsCount} Contact${systemReadiness.contactsCount > 1 ? "s" : ""} Armed`;
            cEl.className = "readiness-value ready";
        } else {
            cEl.textContent = "⚠️ 0 Contacts Configured";
            cEl.className = "readiness-value warning";
        }
    }

    if (badge) {
        const isShieldArmed = (
            (systemReadiness.gesture === "active" || systemReadiness.voice === "listening") &&
            systemReadiness.contactsCount > 0
        );

        if (isShieldArmed) {
            badge.textContent = "🛡️ Full Protection Armed";
            badge.className = "readiness-badge armed";
        } else if (systemReadiness.contactsCount === 0) {
            badge.textContent = "⚠️ Action: Add Contacts";
            badge.className = "readiness-badge partial";
        } else {
            badge.textContent = "🟡 Partial Defense Active";
            badge.className = "readiness-badge partial";
        }
    }
}

function probeGpsReadiness() {
    if (!navigator.geolocation) {
        systemReadiness.gps = "unavailable";
        updateReadinessUI();
        return;
    }
    navigator.geolocation.getCurrentPosition(
        () => {
            systemReadiness.gps = "ready";
            updateReadinessUI();
        },
        () => {
            systemReadiness.gps = "unavailable";
            updateReadinessUI();
        },
        { timeout: 5000, maximumAge: 30000 }
    );
}


/* ============================================================
   ELEMENTS
   ============================================================ */

const authPage =
    document.getElementById("authPage");

const setupPage =
    document.getElementById("setupPage");

const dashboard =
    document.getElementById("dashboard");

const loginForm =
    document.getElementById("loginForm");

const registerForm =
    document.getElementById("registerForm");

const authTitle =
    document.getElementById("authTitle");

const authSubtitle =
    document.getElementById("authSubtitle");

const authMessage =
    document.getElementById("authMessage");

const authSwitchText =
    document.getElementById("authSwitchText");

const authSwitchButton =
    document.getElementById("authSwitchButton");

const toggleVoiceButton =
    document.getElementById("toggleVoiceButton");


/* ============================================================
   AUTH SWITCH
   ============================================================ */

authSwitchButton.addEventListener(
    "click",
    () => {

        const registerVisible =
            !registerForm.classList.contains("hidden");


        if (registerVisible) {

            registerForm.classList.add("hidden");

            loginForm.classList.remove("hidden");

            authTitle.textContent =
                "SOS Guardian";

            authSubtitle.textContent =
                "Your personal emergency protection system.";

            authSwitchText.textContent =
                "Don't have an account?";

            authSwitchButton.textContent =
                "Sign Up";

        } else {

            loginForm.classList.add("hidden");

            registerForm.classList.remove("hidden");

            authTitle.textContent =
                "Create Account";

            authSubtitle.textContent =
                "Create your SOS Guardian account.";

            authSwitchText.textContent =
                "Already have an account?";

            authSwitchButton.textContent =
                "Login";
        }


        clearAuthMessage();
    }
);


/* ============================================================
   AUTH MESSAGE
   ============================================================ */

function showAuthMessage(
    message,
    type = "error"
) {

    authMessage.textContent =
        message;

    authMessage.className =
        `message ${type}`;
}


function clearAuthMessage() {

    authMessage.textContent =
        "";

    authMessage.className =
        "message";
}


/* ============================================================
   REGISTER
   ============================================================ */

registerForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        clearAuthMessage();


        const name =
            document
                .getElementById("registerName")
                .value
                .trim();


        const email =
            document
                .getElementById("registerEmail")
                .value
                .trim();


        const password =
            document
                .getElementById("registerPassword")
                .value;


        try {

            const response =
                await fetch(
                    "/api/auth/register",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            name,
                            email,
                            password
                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                showAuthMessage(
                    data.message ||
                    "Registration failed"
                );

                return;
            }


            currentUser =
                data.user;


            showSetupPage();

        } catch (error) {

            console.error(error);

            showAuthMessage(
                "Cannot connect to SOS Guardian server."
            );
        }
    }
);


/* ============================================================
   LOGIN
   ============================================================ */

loginForm.addEventListener(
    "submit",
    async event => {

        event.preventDefault();

        clearAuthMessage();


        const email =
            document
                .getElementById("loginEmail")
                .value
                .trim();


        const password =
            document
                .getElementById("loginPassword")
                .value;


        try {

            const response =
                await fetch(
                    "/api/auth/login",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            email,
                            password
                        })
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                showAuthMessage(
                    data.message ||
                    "Login failed"
                );

                return;
            }


            currentUser =
                data.user;


            if (
                data.user.protection_enabled
            ) {

                showDashboard();

            } else {

                showSetupPage();
            }

        } catch (error) {

            console.error(error);

            showAuthMessage(
                "Cannot connect to SOS Guardian server."
            );
        }
    }
);


/* ============================================================
   SETUP PAGE
   ============================================================ */

function showSetupPage() {

    authPage.classList.add(
        "hidden"
    );

    dashboard.classList.add(
        "hidden"
    );

    setupPage.classList.remove(
        "hidden"
    );
}


/* ============================================================
   CAMERA PERMISSION
   ============================================================ */

async function requestCameraPermission() {

    try {

        const stream =
            await navigator
                .mediaDevices
                .getUserMedia({
                    video: true
                });


        stream
            .getTracks()
            .forEach(
                track =>
                    track.stop()
            );


        const status =
            document.getElementById(
                "cameraStatus"
            );


        if (status) {

            status.textContent =
                "Allowed";

            status.className =
                "permission-status ready";
        }


        return true;

    } catch (error) {

        console.error(error);


        const status =
            document.getElementById(
                "cameraStatus"
            );


        if (status) {

            status.textContent =
                "Denied";
        }


        return false;
    }
}


/* ============================================================
   MICROPHONE PERMISSION
   ============================================================ */

async function requestMicrophonePermission() {

    try {

        const stream =
            await navigator
                .mediaDevices
                .getUserMedia({
                    audio: true
                });


        stream
            .getTracks()
            .forEach(
                track =>
                    track.stop()
            );


        const status =
            document.getElementById(
                "microphoneStatus"
            );


        if (status) {

            status.textContent =
                "Allowed";

            status.className =
                "permission-status ready";
        }


        return true;

    } catch (error) {

        console.error(error);


        const status =
            document.getElementById(
                "microphoneStatus"
            );


        if (status) {

            status.textContent =
                "Denied";
        }


        return false;
    }
}


/* ============================================================
   LOCATION PERMISSION
   ============================================================ */

async function requestLocationPermission() {

    return new Promise(
        resolve => {

            if (
                !navigator.geolocation
            ) {

                resolve(false);

                return;
            }


            navigator.geolocation
                .getCurrentPosition(

                    () => {

                        const status =
                            document
                                .getElementById(
                                    "locationStatus"
                                );


                        if (status) {

                            status.textContent =
                                "Allowed";

                            status.className =
                                "permission-status ready";
                        }


                        resolve(true);
                    },

                    error => {

                        console.error(
                            error
                        );


                        const status =
                            document
                                .getElementById(
                                    "locationStatus"
                                );


                        if (status) {

                            status.textContent =
                                "Denied";
                        }


                        resolve(false);
                    },

                    {
                        enableHighAccuracy:
                            true,

                        timeout:
                            10000
                    }
                );
        }
    );
}


/* ============================================================
   ENABLE PROTECTION
   ============================================================ */

const enableProtectionButton =
    document.getElementById(
        "enableProtectionButton"
    );


if (enableProtectionButton) {

    enableProtectionButton.addEventListener(
        "click",
        async () => {

            const button =
                enableProtectionButton;


            button.disabled =
                true;

            button.textContent =
                "Requesting permissions...";


            const camera =
                await requestCameraPermission();


            const microphone =
                await requestMicrophonePermission();


            const location =
                await requestLocationPermission();


            try {

                const response =
                    await fetch(
                        "/api/auth/permissions",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({

                                camera_permission:
                                    camera,

                                microphone_permission:
                                    microphone,

                                location_permission:
                                    location
                            })
                        }
                    );


                if (
                    camera &&
                    microphone &&
                    location
                ) {

                    showDashboard();

                } else {

                    button.disabled =
                        false;

                    button.textContent =
                        "Retry Permissions";


                    alert(
                        "Camera, microphone and location permissions are required."
                    );
                }

            } catch (error) {

                console.error(error);

                button.disabled =
                    false;

                button.textContent =
                    "Try Again";
            }
        }
    );
}


/* ============================================================
   DASHBOARD
   ============================================================ */

function showDashboard() {

    authPage.classList.add(
        "hidden"
    );

    setupPage.classList.add(
        "hidden"
    );

    dashboard.classList.remove(
        "hidden"
    );


    if (currentUser) {

        const nameElement =
            document.getElementById(
                "dashboardUserName"
            );


        const welcomeElement =
            document.getElementById(
                "welcomeName"
            );


        if (nameElement) {

            nameElement.textContent =
                currentUser.name;
        }


        if (welcomeElement) {

            welcomeElement.textContent =
                currentUser.name;
        }

        const settingsEmail = document.getElementById("settingsUserEmail");
        if (settingsEmail) {
            settingsEmail.textContent = currentUser.email || currentUser.name || "jyothish";
        }
    }


    loadContacts();

    loadHistory();

    startGestureSystem();

    startVoiceSOS();

    probeGpsReadiness();

    updateReadinessUI();

    if (window.switchDashboardTab) {
        window.switchDashboardTab("tabEmergency");
    }
}


/* ============================================================
   CAMERA
   ============================================================ */

async function startCamera() {

    const video =
        document.getElementById(
            "cameraVideo"
        );


    const status =
        document.getElementById(
            "gestureStatus"
        );


    if (!video) {

        throw new Error(
            "Camera video element not found"
        );
    }


    try {

        cameraStream =
            await navigator
                .mediaDevices
                .getUserMedia({

                    video: {

                        facingMode:
                            "user",

                        width: {
                            ideal: 640
                        },

                        height: {
                            ideal: 480
                        }
                    },

                    audio: false
                });


        video.srcObject =
            cameraStream;


        await video.play();

        systemReadiness.gesture = "active";
        updateReadinessUI();

        if (status) {

            status.textContent =
                "Camera Active";

            status.classList.add(
                "active"
            );
        }

    } catch (error) {

        console.error(
            "Camera error:",
            error
        );

        systemReadiness.gesture = "disabled";
        updateReadinessUI();


        if (status) {

            status.textContent =
                "Camera unavailable";
        }


        throw error;
    }
}


/* ============================================================
   MEDIAPIPE HAND LANDMARKER
   ============================================================ */

async function initializeHandLandmarker() {

    const status =
        document.getElementById(
            "gestureStatus"
        );

    try {

        if (status) {

            status.textContent =
                "Loading hand AI...";
        }

        // Align exact version with vision_bundle.mjs (0.10.21)
        const vision =
            await window
                .FilesetResolver
                .forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm"
                );

        const modelAssetPath =
            "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

        // Attempt GPU delegate first, with automatic fallback to CPU
        try {

            handLandmarker =
                await window
                    .HandLandmarker
                    .createFromOptions(
                        vision,
                        {
                            baseOptions: {
                                modelAssetPath,
                                delegate: "GPU"
                            },
                            runningMode: "VIDEO",
                            numHands: 1,
                            minHandDetectionConfidence: 0.40,
                            minHandPresenceConfidence: 0.40,
                            minTrackingConfidence: 0.40
                        }
                    );

            if (status) {

                status.textContent =
                    "Hand AI Ready (GPU)";

                status.classList.add(
                    "active"
                );
            }

        } catch (gpuError) {

            console.warn(
                "GPU delegate failed; falling back to CPU:",
                gpuError
            );

            handLandmarker =
                await window
                    .HandLandmarker
                    .createFromOptions(
                        vision,
                        {
                            baseOptions: {
                                modelAssetPath,
                                delegate: "CPU"
                            },
                            runningMode: "VIDEO",
                            numHands: 1,
                            minHandDetectionConfidence: 0.40,
                            minHandPresenceConfidence: 0.40,
                            minTrackingConfidence: 0.40
                        }
                    );

            if (status) {

                status.textContent =
                    "Hand AI Ready (CPU)";

                status.classList.add(
                    "active"
                );
            }
        }

    } catch (error) {

        console.error(
            "Hand landmarker initialization error:",
            error
        );

        if (status) {

            status.textContent =
                `Hand AI failed: ${error.message || "Network error"}`;
        }
    }
}


/* ============================================================
   START GESTURE SYSTEM
   ============================================================ */

async function startGestureSystem() {

    try {

        await startCamera();

        await initializeHandLandmarker();

        requestAnimationFrame(
            processGestureFrame
        );

    } catch (error) {

        console.error(
            "Gesture system startup:",
            error
        );
    }
}


/* ============================================================
   HAND MATH
   ============================================================ */

function distance(a, b) {

    const dx =
        a.x - b.x;

    const dy =
        a.y - b.y;

    const dz =
        (a.z || 0) -
        (b.z || 0);


    return Math.sqrt(
        dx * dx +
        dy * dy +
        dz * dz
    );
}


function angle(a, b, c) {

    const ab = {

        x:
            a.x - b.x,

        y:
            a.y - b.y,

        z:
            (a.z || 0) -
            (b.z || 0)
    };


    const cb = {

        x:
            c.x - b.x,

        y:
            c.y - b.y,

        z:
            (c.z || 0) -
            (b.z || 0)
    };


    const dot =
        ab.x * cb.x +
        ab.y * cb.y +
        ab.z * cb.z;


    const ma =
        Math.sqrt(
            ab.x ** 2 +
            ab.y ** 2 +
            ab.z ** 2
        );


    const mc =
        Math.sqrt(
            cb.x ** 2 +
            cb.y ** 2 +
            cb.z ** 2
        );


    if (!ma || !mc) {

        return 0;
    }


    return Math.acos(

        Math.max(
            -1,
            Math.min(
                1,
                dot /
                (ma * mc)
            )
        )

    ) * 180 / Math.PI;
}


function fingerOpen(
    landmarks,
    mcp,
    pip,
    dip,
    tip
) {

    const wrist =
        landmarks[0];

    const tipDist =
        distance(landmarks[tip], wrist);

    const pipDist =
        distance(landmarks[pip], wrist);

    const mcpDist =
        distance(landmarks[mcp], wrist);

    const isExtended =
        tipDist > pipDist * 1.05 &&
        pipDist > mcpDist * 0.95;

    const jointAngle =
        angle(
            landmarks[pip],
            landmarks[dip],
            landmarks[tip]
        );

    return isExtended && jointAngle > 125;
}


function thumbOpen(
    landmarks
) {

    const wrist =
        landmarks[0];

    const thumbTip =
        landmarks[4];

    const thumbIP =
        landmarks[3];

    const thumbMCP =
        landmarks[2];

    const indexMCP =
        landmarks[5];

    const pinkyMCP =
        landmarks[17];

    const tipToPinky =
        distance(thumbTip, pinkyMCP);

    const ipToPinky =
        distance(thumbIP, pinkyMCP);

    const tipToIndex =
        distance(thumbTip, indexMCP);

    const mcpToIndex =
        distance(thumbMCP, indexMCP);

    const tipToWrist =
        distance(thumbTip, wrist);

    const ipToWrist =
        distance(thumbIP, wrist);

    const isAbducted =
        tipToPinky > ipToPinky * 0.98;

    const isSeparated =
        tipToIndex > mcpToIndex * 1.1;

    const isNotCurled =
        tipToWrist > ipToWrist * 0.95;

    return isAbducted && (isSeparated || isNotCurled);
}


function detectOpenPalm(
    landmarks
) {

    if (
        !landmarks ||
        landmarks.length !== 21
    ) {

        return {
            detected: false,
            fingers: 0,
            thumb: false
        };
    }

    const index =
        fingerOpen(landmarks, 5, 6, 7, 8);

    const middle =
        fingerOpen(landmarks, 9, 10, 11, 12);

    const ring =
        fingerOpen(landmarks, 13, 14, 15, 16);

    const pinky =
        fingerOpen(landmarks, 17, 18, 19, 20);

    const thumb =
        thumbOpen(landmarks);

    const fingers =
        [
            index,
            middle,
            ring,
            pinky
        ]
        .filter(Boolean)
        .length;

    return {
        detected:
            fingers === 4 &&
            thumb,
        fingers,
        thumb
    };
}


/* ============================================================
   PROCESS CAMERA FRAMES
   ============================================================ */

async function processGestureFrame() {

    const video =
        document.getElementById(
            "cameraVideo"
        );


    if (
        !handLandmarker ||
        !video ||
        video.readyState < 2 ||
        video.videoWidth === 0
    ) {

        requestAnimationFrame(
            processGestureFrame
        );

        return;
    }


    if (
        video.currentTime !==
        lastVideoTime
    ) {

        lastVideoTime =
            video.currentTime;


        try {

            let timestamp =
                performance.now();

            if (timestamp <= lastDetectionTimestamp) {
                timestamp = lastDetectionTimestamp + 1;
            }

            lastDetectionTimestamp =
                timestamp;

            const results =
                handLandmarker
                    .detectForVideo(
                        video,
                        timestamp
                    );


            handleGestureResult(
                results
            );

        } catch (error) {

            console.error(
                "Hand detection:",
                error
            );
        }
    }


    requestAnimationFrame(
        processGestureFrame
    );
}


/* ============================================================
   HANDLE HAND GESTURE (TEMPORAL DEBOUNCE)
   ============================================================ */

function handleGestureResult(
    results
) {

    const text =
        document.getElementById(
            "gestureText"
        );


    if (!text) {

        return;
    }

    const now =
        performance.now();


    if (
        !results ||
        !results.landmarks ||
        !results.landmarks.length
    ) {

        if (
            palmLastSeenTime &&
            (now - palmLastSeenTime > 400)
        ) {

            palmStartTime =
                null;

            palmLastSeenTime =
                null;

            text.textContent =
                "Waiting for hand...";

            text.className =
                "gesture-waiting";
        }

        return;
    }


    const palm =
        detectOpenPalm(
            results.landmarks[0]
        );


    if (!palm.detected) {

        if (
            palmLastSeenTime &&
            (now - palmLastSeenTime > 350)
        ) {

            palmStartTime =
                null;

            palmLastSeenTime =
                null;

            text.textContent =
                `Hand detected — open palm ✋ (${palm.fingers}/4 fingers${palm.thumb ? ' + thumb' : ''})`;

            text.className =
                "gesture-waiting";
        }

        return;
    }


    palmLastSeenTime =
        now;

    if (!palmStartTime) {

        palmStartTime =
            now;
    }


    const held =
        now -
        palmStartTime;


    const progressSeconds =
        Math.min(
            2.0,
            held / 1000
        ).toFixed(1);

    text.textContent =
        `✋ OPEN PALM — hold ${progressSeconds} / 2.0 sec`;


    text.className =
        "gesture-detected";


    if (

        held >= 2000 &&

        !gestureSosTriggered &&

        Date.now() >
        gestureCooldownUntil

    ) {

        gestureSosTriggered =
            true;

        palmStartTime =
            null;

        palmLastSeenTime =
            null;


        startSosCountdown(
            "hand_gesture"
        );
    }
}


/* ============================================================
   MANUAL SOS BUTTON
   ============================================================ */

const sosButton =
    document.getElementById(
        "sosButton"
    );


if (sosButton) {

    sosButton.addEventListener(
        "click",
        () => {

            startSosCountdown(
                "button"
            );
        }
    );
}


/* ============================================================
   SOS COUNTDOWN
   ============================================================ */

function startSosCountdown(
    triggerType = "button"
) {

    if (countdownTimer) {

        return;
    }


    countdownValue =
        5;


    const number =
        document.getElementById(
            "countdownNumber"
        );


    const modal =
        document.getElementById(
            "countdownModal"
        );


    if (number) {

        number.textContent =
            countdownValue;
    }


    if (modal) {

        modal.classList.remove(
            "hidden"
        );
    }


    countdownTimer =
        setInterval(
            () => {

                countdownValue--;


                if (number) {

                    number.textContent =
                        countdownValue;
                }


                if (
                    countdownValue <= 0
                ) {

                    clearInterval(
                        countdownTimer
                    );


                    countdownTimer =
                        null;


                    triggerSOS(
                        triggerType
                    );
                }

            },
            1000
        );
}


/* ============================================================
   CANCEL SOS
   ============================================================ */

const cancelSosButton =
    document.getElementById(
        "cancelSosButton"
    );


if (cancelSosButton) {

    cancelSosButton.addEventListener(
        "click",
        () => {

            clearInterval(
                countdownTimer
            );


            countdownTimer =
                null;


            const modal =
                document.getElementById(
                    "countdownModal"
                );


            if (modal) {

                modal.classList.add(
                    "hidden"
                );
            }


            gestureSosTriggered =
                false;


            palmStartTime =
                null;


            voiceTriggered =
                false;

            voiceCooldownUntil =
                0;

            if (voiceEnabled && voiceRunning) {
                updateVoiceStatus(
                    "🎤 Listening for emergency words...",
                    "listening"
                );
            }
        }
    );
}


/* ============================================================
   TRIGGER SOS (RESILIENT GEOLOCATION)
   ============================================================ */

async function sendSosRequest(
    latitude,
    longitude,
    triggerType
) {

    try {

        const response =
            await fetch(
                "/api/sos",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            latitude,
                            longitude,
                            trigger_type:
                                triggerType
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            alert(
                data.message ||
                "SOS failed."
            );

            gestureSosTriggered =
                false;

            voiceTriggered =
                false;

            voiceCooldownUntil =
                0;

            return;
        }

        const locNote =
            data.event?.location_available
                ? "📍 Location coordinates attached."
                : "⚠️ Location unavailable — alert dispatched without GPS.";

        alert(
            `🚨 SOS ACTIVATED!\n\n` +
            `Emergency event recorded.\n${locNote}`
        );

        loadHistory();

        const activeEventId = data.event_id || data.event?.id;
        if (activeEventId) {
            activateLiveEmergencyDashboard(activeEventId, data.event, data.tracking_url);
        }

        setTimeout(
            () => {

                gestureSosTriggered =
                    false;

                voiceTriggered =
                    false;

            },
            3000
        );

    } catch (error) {

        console.error(
            "SOS Network Error:",
            error
        );

        alert(
            "Could not connect to SOS Guardian backend."
        );

        gestureSosTriggered =
            false;

        voiceTriggered =
            false;
    }
}


function triggerSOS(
    triggerType
) {

    const modal =
        document.getElementById(
            "countdownModal"
        );

    if (modal) {

        modal.classList.add(
            "hidden"
        );
    }

    if (
        triggerType ===
        "hand_gesture"
    ) {

        gestureCooldownUntil =
            Date.now() + 15000;
    }

    if (
        triggerType ===
        "voice"
    ) {

        voiceTriggered =
            false;

        voiceCooldownUntil =
            Date.now() + 15000;
    }

    if (
        !navigator.geolocation
    ) {

        console.warn(
            "Geolocation unavailable; dispatching SOS without GPS."
        );

        sendSosRequest(
            null,
            null,
            triggerType
        );

        return;
    }

    let dispatched =
        false;

    const locationTimeout =
        setTimeout(
            () => {

                if (!dispatched) {

                    dispatched =
                        true;

                    console.warn(
                        "GPS acquisition timed out; dispatching SOS without GPS."
                    );

                    sendSosRequest(
                        null,
                        null,
                        triggerType
                    );
                }

            },
            3500
        );

    navigator.geolocation
        .getCurrentPosition(

            position => {

                if (dispatched) {
                    return;
                }

                dispatched =
                    true;

                clearTimeout(
                    locationTimeout
                );

                sendSosRequest(
                    position.coords.latitude,
                    position.coords.longitude,
                    triggerType
                );
            },

            error => {

                if (dispatched) {
                    return;
                }

                dispatched =
                    true;

                clearTimeout(
                    locationTimeout
                );

                console.warn(
                    "GPS permission denied or failed:",
                    error.message
                );

                sendSosRequest(
                    null,
                    null,
                    triggerType
                );
            },

            {
                enableHighAccuracy:
                    true,

                timeout:
                    3000,

                maximumAge:
                    10000
            }
        );
}


/* ============================================================
   VOICE SOS ENGINE
   ============================================================ */

const EMERGENCY_VOICE_REGEX =
    /\b(sos|help\s+me|i\s+need\s+help|please\s+help|emergency|save\s+me|call\s+for\s+help|sos\s+guardian)\b/i;

function startVoiceSOS() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        console.warn(
            "Speech Recognition is not supported by this browser."
        );

        updateVoiceStatus(
            "Voice SOS not supported in this browser.",
            "error"
        );

        updateVoiceTranscript(
            "Web Speech Recognition API is unavailable in this browser."
        );

        if (toggleVoiceButton) {
            toggleVoiceButton.disabled = true;
            toggleVoiceButton.textContent = "Voice Unsupported";
        }

        systemReadiness.voice = "disabled";
        updateReadinessUI();

        return;
    }

    if (!voiceEnabled || voiceRunning) {
        return;
    }

    try {

        voiceRecognition =
            new SpeechRecognition();

        voiceRecognition.continuous =
            true;

        voiceRecognition.interimResults =
            true;

        voiceRecognition.lang =
            "en-US";

        voiceRecognition.onstart =
            () => {

                voiceRunning =
                    true;

                systemReadiness.voice =
                    "listening";
                updateReadinessUI();

                console.log(
                    "🎤 Voice SOS listening..."
                );

                updateVoiceStatus(
                    "🎤 Listening for emergency words...",
                    "listening"
                );
            };

        voiceRecognition.onresult =
            event => {

                let interimTranscript = "";
                let finalTranscript = "";

                for (
                    let i = event.resultIndex;
                    i < event.results.length;
                    i++
                ) {
                    const text = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += text + " ";
                    } else {
                        interimTranscript += text + " ";
                    }
                }

                const fullTranscript =
                    (finalTranscript + interimTranscript).trim();

                if (fullTranscript) {
                    updateVoiceTranscript(`"${fullTranscript}"`);
                    checkEmergencyVoice(fullTranscript);
                }
            };

        voiceRecognition.onerror =
            event => {

                console.warn(
                    "Voice recognition error:",
                    event.error
                );

                if (
                    event.error === "not-allowed" ||
                    event.error === "service-not-allowed"
                ) {

                    voiceEnabled = false;
                    voiceRunning = false;
                    systemReadiness.voice = "disabled";
                    updateReadinessUI();

                    updateVoiceStatus(
                        "🎤 Microphone permission denied.",
                        "error"
                    );

                    updateVoiceTranscript(
                        "Microphone access blocked. Enable permissions to use Voice SOS."
                    );

                    if (toggleVoiceButton) {
                        toggleVoiceButton.textContent = "Mic Blocked";
                        toggleVoiceButton.disabled = true;
                    }

                    return;
                }

                if (event.error === "no-speech") {
                    // Normal idle timeout in quiet environments; automatically restarts on onend
                    return;
                }

                if (event.error === "network") {
                    updateVoiceStatus(
                        "Speech network connection issue — retrying...",
                        "error"
                    );
                }
            };

        voiceRecognition.onend =
            () => {

                voiceRunning =
                    false;

                /*
                   Automatically restart speech
                   recognition if voice is enabled and
                   the user is still logged into the dashboard.
                */

                if (
                    voiceEnabled &&
                    currentUser &&
                    dashboard &&
                    !dashboard.classList.contains("hidden")
                ) {

                    setTimeout(
                        () => {

                            if (!voiceRunning && voiceEnabled) {
                                startVoiceSOS();
                            }

                        },
                        600
                    );
                }
            };

        voiceRecognition.start();

    } catch (error) {

        console.error(
            "Voice startup error:",
            error
        );

        voiceRunning =
            false;

        updateVoiceStatus(
            "Voice SOS startup failed.",
            "error"
        );
    }
}


/* ============================================================
   CHECK EMERGENCY VOICE
   ============================================================ */

function checkEmergencyVoice(
    transcript
) {

    if (
        !voiceEnabled ||
        voiceTriggered ||
        countdownTimer ||
        Date.now() < voiceCooldownUntil
    ) {
        return;
    }

    const match = transcript.match(EMERGENCY_VOICE_REGEX);

    if (!match) {
        return;
    }

    const detectedPhrase = match[0].toUpperCase();

    console.log(
        `🚨 EMERGENCY VOICE DETECTED [${detectedPhrase}]:`,
        transcript
    );

    voiceTriggered =
        true;

    voiceCooldownUntil =
        Date.now() + 15000;

    updateVoiceStatus(
        `🚨 Emergency voice detected ("${detectedPhrase}")!`,
        "active"
    );

    updateVoiceTranscript(
        `Trigger phrase matched: "${match[0]}" in "${transcript}"`
    );

    startSosCountdown(
        "voice"
    );

    setTimeout(
        () => {

            if (!countdownTimer) {

                voiceTriggered =
                    false;

                if (voiceRunning && voiceEnabled) {

                    updateVoiceStatus(
                        "🎤 Listening for emergency words...",
                        "listening"
                    );
                }
            }

        },
        10000
    );
}


/* ============================================================
   VOICE TELEMETRY & CONTROLS
   ============================================================ */

function updateVoiceStatus(
    message,
    statusClass = ""
) {

    const element =
        document.getElementById("voiceStatus");

    if (element) {

        element.textContent =
            message;

        element.className =
            "voice-status" + (statusClass ? ` ${statusClass}` : "");
    }
}


function updateVoiceTranscript(
    text
) {

    const element =
        document.getElementById("voiceTranscript");

    if (element) {

        element.textContent =
            text;
    }
}


function toggleVoiceSOS() {

    voiceEnabled = !voiceEnabled;

    const btn =
        document.getElementById("toggleVoiceButton");

    if (!voiceEnabled) {

        stopVoiceSOS();

        systemReadiness.voice = "paused";
        updateReadinessUI();

        if (btn) {
            btn.textContent = "Resume Voice SOS";
            btn.classList.add("paused");
        }

        updateVoiceStatus(
            "Voice SOS Paused",
            "paused"
        );

        updateVoiceTranscript(
            "Voice recognition paused by user."
        );

    } else {

        systemReadiness.voice = "listening";
        updateReadinessUI();

        if (btn) {
            btn.textContent = "Pause Voice SOS";
            btn.classList.remove("paused");
        }

        updateVoiceStatus(
            "Starting voice listener...",
            "listening"
        );

        updateVoiceTranscript(
            "Listening for voice input..."
        );

        startVoiceSOS();
    }
}


if (toggleVoiceButton) {

    toggleVoiceButton.addEventListener(
        "click",
        () => {
            toggleVoiceSOS();
        }
    );
}


/* ============================================================
   STOP VOICE
   ============================================================ */

function stopVoiceSOS() {

    if (voiceRecognition) {

        try {

            voiceRecognition.stop();

        } catch (error) {

            console.warn(
                "Voice stop:",
                error
            );
        }
    }

    voiceRunning =
        false;
}


/* ============================================================
   CONTACTS
   ============================================================ */

async function loadContacts() {

    try {

        const response =
            await fetch(
                "/api/contacts"
            );


        if (!response.ok) {

            return;
        }


        const data =
            await response.json();

        systemReadiness.contactsCount =
            (data.contacts && Array.isArray(data.contacts))
                ? data.contacts.length
                : 0;

        updateReadinessUI();


        const list =
            document.getElementById(
                "contactList"
            );


        if (!list) {

            return;
        }


        if (
            !data.contacts ||
            data.contacts.length === 0
        ) {

            list.innerHTML =
                `<div class="empty">
                    No emergency contacts added yet.
                </div>`;

            return;
        }


        list.innerHTML =
            data.contacts
                .map(
                    contact => `

                    <div class="contact-item">

                        <div>

                            <div class="contact-name">

                                ${escapeHtml(
                                    contact.name
                                )}
                                <span class="tier-badge ${contact.priority === 3 ? 'tier-badge-3' : (contact.priority === 2 ? 'tier-badge-2' : 'tier-badge-1')}">
                                    ${contact.priority === 3 ? 'Tier 3: Backup' : (contact.priority === 2 ? 'Tier 2: Escalation' : 'Tier 1: Primary')}
                                </span>

                            </div>

                            <div class="contact-phone">

                                ${escapeHtml(
                                    contact.phone
                                )}
                                ${contact.telegram_chat_id ? `<br><small style="color:#60a5fa">✈️ ${escapeHtml(contact.telegram_chat_id)}</small>` : ""}

                            </div>

                        </div>


                        <div class="contact-actions">

                            <button
                                class="test-contact-btn"
                                type="button"
                                onclick="testContactNotification(${contact.id}, '${escapeHtml(contact.name)}')"
                                title="Send a test notification to verify delivery"
                            >
                                🧪 Test
                            </button>

                            <button
                                class="delete-btn"
                                onclick="deleteContact(${contact.id})"
                            >
                                Delete
                            </button>

                        </div>

                    </div>

                    `
                )
                .join("");

    } catch (error) {

        console.error(
            error
        );
    }
}


/* ============================================================
   ADD CONTACT
   ============================================================ */

const contactForm =
    document.getElementById(
        "contactForm"
    );


if (contactForm) {

    contactForm.addEventListener(
        "submit",
        async event => {

            event.preventDefault();


            const name =
                document
                    .getElementById(
                        "contactName"
                    )
                    .value
                    .trim();


            const phone =
                document
                    .getElementById(
                        "contactPhone"
                    )
                    .value
                    .trim();

            const telegram_chat_id =
                (document
                    .getElementById(
                        "contactTelegram"
                    )
                    ?.value || "")
                    .trim() || null;

            const priority =
                parseInt(document.getElementById("contactPriority")?.value || "1", 10);

            try {

                const response =
                    await fetch(
                        "/api/contacts",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    name,
                                    phone,
                                    telegram_chat_id,
                                    priority
                                })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    alert(
                        data.message ||
                        "Failed to add contact"
                    );

                    return;
                }


                document
                    .getElementById(
                        "contactName"
                    )
                    .value = "";


                document
                    .getElementById(
                        "contactPhone"
                    )
                    .value = "";

                const tgElem =
                    document.getElementById(
                        "contactTelegram"
                    );

                if (tgElem) {
                    tgElem.value = "";
                }


                loadContacts();

            } catch (error) {

                console.error(
                    error
                );
            }
        }
    );
}


/* ============================================================
   DELETE CONTACT
   ============================================================ */

async function deleteContact(
    contactId
) {

    if (
        !confirm(
            "Delete this emergency contact?"
        )
    ) {

        return;
    }


    try {

        const response =
            await fetch(
                `/api/contacts/${contactId}`,
                {
                    method:
                        "DELETE"
                }
            );

        const data = await response.json();

        if (response.ok) {
            loadContacts();
        } else {
            alert(data.message || "Failed to delete contact");
        }

    } catch (error) {

        console.error(
            error
        );
        alert("Error deleting contact: " + error.message);
    }
}


window.deleteContact =
    deleteContact;


async function testContactNotification(
    contactId,
    contactName
) {

    try {

        const response =
            await fetch(
                `/api/contacts/${contactId}/test`,
                {
                    method:
                        "POST"
                }
            );

        const data =
            await response.json();

        if (response.ok) {

            let msg =
                `🧪 Test Notification Dispatched to ${contactName}!\n\n`;

            if (data.results?.sms) {

                const s = data.results.sms;

                msg +=
                    `📱 SMS (${s.provider || "mock"}): ${s.status || (s.success ? "sent" : "failed")}\n`;

                if (s.note) {
                    msg += `   ℹ️ ${s.note}\n`;
                }

                if (s.error) {
                    msg += `   ⚠️ ${s.error}\n`;
                }
            }

            if (data.results?.telegram) {

                const t = data.results.telegram;

                msg +=
                    `✈️ Telegram: ${t.status || (t.success ? "sent" : "failed")}\n`;

                if (t.note) {
                    msg += `   ℹ️ ${t.note}\n`;
                }

                if (t.error) {
                    msg += `   ⚠️ ${t.error}\n`;
                }
            }

            alert(msg);

        } else {

            alert(
                data.message ||
                "Could not send test notification."
            );
        }

    } catch (error) {

        console.error(
            "Test contact error:",
            error
        );

        alert(
            "Failed to connect to server for test notification."
        );
    }
}

window.testContactNotification =
    testContactNotification;


/* ============================================================
   SOS HISTORY
   ============================================================ */

async function loadHistory() {

    try {

        const response =
            await fetch(
                "/api/sos/history"
            );


        if (!response.ok) {

            return;
        }


        const data =
            await response.json();


        const list =
            document.getElementById(
                "historyList"
            );


        if (!list) {

            return;
        }


        if (
            !data.events ||
            data.events.length === 0
        ) {

            list.innerHTML =
                `<div class="empty">
                    No SOS events yet.
                </div>`;

            return;
        }


        list.innerHTML =
            data.events
                .map(
                    event => {

                        const date =
                            new Date(
                                event.created_at
                            )
                            .toLocaleString();

                        const locationText =
                            (event.latitude !== null && event.longitude !== null)
                                ? `${event.latitude}, ${event.longitude}`
                                : "Unavailable (No GPS)";

                        const locationLink =
                            event.maps_url
                                ? `<a href="${escapeHtml(event.maps_url)}" target="_blank">📍 Open Location</a>`
                                : `<span style="color:#94a3b8; font-size:12px;">📍 Location Unavailable</span>`;

                        const notifHtml =
                            (event.notifications && event.notifications.length > 0)
                                ? `<div style="margin-top: 8px; display:flex; flex-wrap:wrap; gap:6px;">
                                    ${event.notifications.map(n => {
                                        const icon = n.channel === "telegram" ? "✈️" : "📱";
                                        const isSent = n.status === "sent";
                                        const isSim = n.status === "simulated";
                                        const color = isSent ? "#15803d" : (isSim ? "#1d4ed8" : "#b91c1c");
                                        const bg = isSent ? "#dcfce7" : (isSim ? "#dbeafe" : "#fee2e2");
                                        return `<span style="display:inline-flex; align-items:center; gap:4px; padding:3px 7px; border-radius:6px; background:${bg}; color:${color}; font-size:11px; font-weight:700;">
                                            ${icon} ${escapeHtml(n.channel)}: ${escapeHtml(n.status)}
                                        </span>`;
                                    }).join("")}
                                   </div>`
                                : "";

                        return `

                        <div class="history-item">

                            <div class="history-title">

                                🚨 SOS Event #${event.id}

                            </div>


                            <div class="history-meta">

                                Trigger:
                                ${escapeHtml(
                                    event.trigger_type
                                )}

                                <br>

                                Status:
                                <strong>${escapeHtml(
                                    event.status
                                )}</strong>

                                <br>

                                Location:
                                ${locationText}

                                <br>

                                ${date}

                                ${notifHtml}

                            </div>


                            <br>


                            ${locationLink}

                        </div>

                        `;
                    }
                )
                .join("");

    } catch (error) {

        console.error(
            error
        );
    }
}


/* ============================================================
   LOGOUT
   ============================================================ */

const logoutButton =
    document.getElementById(
        "logoutButton"
    );


if (logoutButton) {

    logoutButton.addEventListener(
        "click",
        async () => {

            try {

                await fetch(
                    "/api/auth/logout",
                    {
                        method:
                            "POST"
                    }
                );

            } catch (error) {

                console.error(
                    error
                );
            }


            stopVoiceSOS();


            if (cameraStream) {

                cameraStream
                    .getTracks()
                    .forEach(
                        track =>
                            track.stop()
                    );


                cameraStream =
                    null;
            }


            currentUser =
                null;


            handLandmarker =
                null;


            gestureSosTriggered =
                false;


            voiceTriggered =
                false;

            voiceCooldownUntil =
                0;


            dashboard.classList.add(
                "hidden"
            );


            setupPage.classList.add(
                "hidden"
            );


            authPage.classList.remove(
                "hidden"
            );


            loginForm.reset();

            registerForm.reset();

            clearAuthMessage();
        }
    );
}


/* ============================================================
   HTML ESCAPE
   ============================================================ */

function escapeHtml(
    value
) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );
}


/* ============================================================
   EXISTING SESSION
   ============================================================ */

async function checkExistingSession() {

    try {

        const response =
            await fetch(
                "/api/auth/me"
            );


        if (!response.ok) {

            return;
        }


        const data =
            await response.json();


        if (
            data.authenticated
        ) {

            currentUser =
                data.user;


            if (
                data.user.protection_enabled
            ) {

                showDashboard();

            } else {

                showSetupPage();
            }
        }

    } catch (error) {

        console.log(
            "No active session."
        );
    }
}


/* ============================================================
   START APPLICATION
   ============================================================ */

checkExistingSession();


/* ============================================================
   PHASE 6: INTELLIGENT FEATURES — LIVE TRACKING & BREADCRUMBS
   ============================================================ */

let activeEmergencyId = null;
let liveGeolocationWatchId = null;
let breadcrumbStreamCount = 0;
let escalationTimerInterval = null;
let escalationSecondsRemaining = 60;
let currentEscalationTier = 1;

function activateLiveEmergencyDashboard(eventId, eventData, trackingUrl) {
    activeEmergencyId = eventId;
    breadcrumbStreamCount = 1;
    escalationSecondsRemaining = 60;
    currentEscalationTier = 1;

    // Automatically switch to Emergency Center tab so user sees live incident hub
    const emergencyTabBtn = document.querySelector(`.dashboard-tabs .tab-btn[data-tab="tabEmergency"]`);
    if (emergencyTabBtn && !emergencyTabBtn.classList.contains("active")) {
        emergencyTabBtn.click();
    }

    const panel = document.getElementById("activeEmergencyPanel");
    if (panel) panel.classList.remove("hidden");

    const idBadge = document.getElementById("activeEventIdBadge");
    if (idBadge) idBadge.textContent = `Event #${eventId}`;

    const tierBadge = document.getElementById("activeEscalationBadge");
    if (tierBadge) tierBadge.textContent = "Tier 1: Primary";

    const breadcrumbsCountElem = document.getElementById("activeBreadcrumbsCount");
    if (breadcrumbsCountElem) breadcrumbsCountElem.textContent = "1 breadcrumb streamed";

    const coordsText = document.getElementById("activeCoordinatesText");
    if (coordsText) {
        coordsText.textContent = (eventData?.latitude && eventData?.longitude)
            ? `${eventData.latitude.toFixed(4)}, ${eventData.longitude.toFixed(4)}`
            : "GPS fix pending...";
    }

    const trackingLink = document.getElementById("btnTrackingMapLink");
    if (trackingLink) {
        trackingLink.href = trackingUrl || `/api/sos/${eventId}/tracking`;
    }

    startLiveBreadcrumbsWatcher(eventId);
    startEscalationCountdown(eventId);
}

function startLiveBreadcrumbsWatcher(eventId) {
    if (liveGeolocationWatchId !== null) {
        navigator.geolocation?.clearWatch(liveGeolocationWatchId);
    }

    if (!navigator.geolocation) return;

    let lastStreamTime = 0;
    liveGeolocationWatchId = navigator.geolocation.watchPosition(
        async position => {
            const now = Date.now();
            if (now - lastStreamTime < 8000) return;
            lastStreamTime = now;

            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            const accuracy = position.coords.accuracy;
            const speed = position.coords.speed;

            try {
                const res = await fetch(`/api/sos/${eventId}/location`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ latitude: lat, longitude: lng, accuracy, speed })
                });

                if (res.ok) {
                    breadcrumbStreamCount++;
                    const countElem = document.getElementById("activeBreadcrumbsCount");
                    if (countElem) countElem.textContent = `${breadcrumbStreamCount} breadcrumbs streamed`;

                    const coordsText = document.getElementById("activeCoordinatesText");
                    if (coordsText) coordsText.textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)} (±${Math.round(accuracy)}m)`;
                }
            } catch (err) {
                console.warn("Breadcrumb stream error:", err);
            }
        },
        err => console.warn("Watch position error:", err),
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );
}

function startEscalationCountdown(eventId) {
    if (escalationTimerInterval) clearInterval(escalationTimerInterval);

    const countdownText = document.getElementById("escalationCountdownText");
    const isAutoEscalation = localStorage.getItem("sos_auto_escalation") === "true";

    // Default: Single Alert Mode — Prevent repeat messages
    if (!isAutoEscalation) {
        if (countdownText) {
            countdownText.textContent = "Single Alert Mode (Auto-escalation disabled)";
        }
        return;
    }

    escalationSecondsRemaining = 60;
    escalationTimerInterval = setInterval(() => {
        escalationSecondsRemaining--;
        if (countdownText) {
            countdownText.textContent = `Auto-escalating to Tier ${currentEscalationTier + 1} in ${escalationSecondsRemaining}s`;
        }

        if (escalationSecondsRemaining <= 0) {
            clearInterval(escalationTimerInterval);
            escalateEmergency(eventId);
        }
    }, 1000);
}

async function escalateEmergency(eventId) {
    if (!eventId) eventId = activeEmergencyId;
    if (!eventId) return;

    try {
        const res = await fetch(`/api/sos/${eventId}/escalate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        const data = await res.json();
        if (res.ok) {
            currentEscalationTier = data.escalation_level;
            const tierBadge = document.getElementById("activeEscalationBadge");
            if (tierBadge) tierBadge.textContent = `Tier ${currentEscalationTier} Escalated`;

            const statusText = document.getElementById("escalationStatusText");
            if (statusText) statusText.textContent = `Tier ${currentEscalationTier} Escalated`;

            const countdownText = document.getElementById("escalationCountdownText");
            if (countdownText) countdownText.textContent = "Higher priority alert dispatched to next tier";

            alert(`🚨 EMERGENCY ESCALATED!\n\nAlert level escalated to Tier ${currentEscalationTier}. Higher tier guardians have been notified.`);
        } else {
            alert(data.message || "Could not escalate alert.");
        }
    } catch (err) {
        console.error("Escalation error:", err);
    }
}

async function acknowledgeEmergency(eventId) {
    if (!eventId) eventId = activeEmergencyId;
    if (!eventId) return;

    const responder = prompt("Enter responder or guardian name / unit:", "Responder On Scene");
    if (!responder) return;

    try {
        const res = await fetch(`/api/sos/${eventId}/acknowledge`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acknowledged_by: responder })
        });

        const data = await res.json();
        if (res.ok) {
            if (escalationTimerInterval) clearInterval(escalationTimerInterval);
            const ackStatus = document.getElementById("acknowledgementStatusText");
            if (ackStatus) ackStatus.textContent = "✅ Acknowledged";

            const ackBy = document.getElementById("acknowledgedByText");
            if (ackBy) ackBy.textContent = `By: ${escapeHtml(responder)}`;

            const countdownText = document.getElementById("escalationCountdownText");
            if (countdownText) countdownText.textContent = "Escalation halted (acknowledged)";

            alert(`✅ EMERGENCY ACKNOWLEDGED!\n\nResponder recorded: ${responder}.\nFurther automatic escalations have been halted.`);
        }
    } catch (err) {
        console.error("Acknowledge error:", err);
    }
}

document.getElementById("btnManualEscalate")?.addEventListener("click", () => {
    escalateEmergency(activeEmergencyId);
});

document.getElementById("btnAcknowledgeAlert")?.addEventListener("click", () => {
    acknowledgeEmergency(activeEmergencyId);
});


/* ============================================================
   PHASE 6: INTELLIGENT FALL & IMPACT DETECTION
   ============================================================ */

let fallCountdownInterval = null;
let fallSecondsRemaining = 15;
let audioCtx = null;

function playWarningChime() {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === "suspended") {
            audioCtx.resume();
        }
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.3);
        gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {
        // AudioContext may require user interaction
    }
}

function launchFallPrompt() {
    const modal = document.getElementById("fallModal");
    if (!modal) return;

    modal.classList.remove("hidden");
    fallSecondsRemaining = 15;
    const counter = document.getElementById("fallCountdownNumber");
    if (counter) counter.textContent = fallSecondsRemaining;

    playWarningChime();

    if (fallCountdownInterval) clearInterval(fallCountdownInterval);
    fallCountdownInterval = setInterval(() => {
        fallSecondsRemaining--;
        if (counter) counter.textContent = fallSecondsRemaining;
        if (fallSecondsRemaining % 3 === 0) playWarningChime();

        if (fallSecondsRemaining <= 0) {
            clearInterval(fallCountdownInterval);
            modal.classList.add("hidden");
            triggerSOS("fall_detection");
        }
    }, 1000);
}

document.getElementById("btnFallCancel")?.addEventListener("click", () => {
    if (fallCountdownInterval) clearInterval(fallCountdownInterval);
    const modal = document.getElementById("fallModal");
    if (modal) modal.classList.add("hidden");
    alert("✅ Fall alarm cancelled. Recorded that you are safe!");
});

document.getElementById("btnFallSosNow")?.addEventListener("click", () => {
    if (fallCountdownInterval) clearInterval(fallCountdownInterval);
    const modal = document.getElementById("fallModal");
    if (modal) modal.classList.add("hidden");
    triggerSOS("fall_detection");
});

document.getElementById("btnSimulateFall")?.addEventListener("click", () => {
    launchFallPrompt();
});

if (window.DeviceMotionEvent) {
    let lastSpikeTime = 0;
    window.addEventListener("devicemotion", event => {
        const acc = event.accelerationIncludingGravity || event.acceleration;
        if (!acc) return;
        const mag = Math.sqrt((acc.x || 0)**2 + (acc.y || 0)**2 + (acc.z || 0)**2);
        if (mag > 26 && Date.now() - lastSpikeTime > 20000) {
            lastSpikeTime = Date.now();
            console.warn("⚠️ Motion impact detected:", mag.toFixed(1), "m/s² — Launching Fall Verification.");
            launchFallPrompt();
        }
    });
}


/* ============================================================
   PHASE 6: SAFETY CHECK-IN TIMER
   ============================================================ */

let safetyCheckinInterval = null;

async function initSafetyCheckin() {
    try {
        const res = await fetch("/api/safety-checkin/status");
        if (!res.ok) return;
        const data = await res.json();
        if (data.active && data.checkin) {
            showActiveCheckinUI(data.checkin, data.remaining_seconds);
        }
    } catch (err) {
        console.warn("Safety checkin init error:", err);
    }
}

function showActiveCheckinUI(checkin, remainingSeconds) {
    const setupBox = document.getElementById("checkinSetupBox");
    const activeBox = document.getElementById("checkinActiveBox");
    const badge = document.getElementById("checkinStatusBadge");
    const noteElem = document.getElementById("checkinActiveNote");

    if (setupBox) setupBox.classList.add("hidden");
    if (activeBox) activeBox.classList.remove("hidden");
    if (badge) {
        badge.className = "sensor-badge active";
        badge.textContent = "⏱️ Active Timer";
    }
    if (noteElem) {
        noteElem.textContent = checkin.note ? `Note: "${escapeHtml(checkin.note)}"` : "No custom note attached";
    }

    startSafetyCheckinCountdown(remainingSeconds);
}

function startSafetyCheckinCountdown(totalSeconds) {
    if (safetyCheckinInterval) clearInterval(safetyCheckinInterval);
    let secondsLeft = Math.max(0, totalSeconds);

    const display = document.getElementById("checkinTimeRemaining");

    const updateDisplay = () => {
        const mins = Math.floor(secondsLeft / 60);
        const secs = secondsLeft % 60;
        if (display) {
            display.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
        }
    };

    updateDisplay();
    safetyCheckinInterval = setInterval(async () => {
        secondsLeft--;
        updateDisplay();

        if (secondsLeft <= 0) {
            clearInterval(safetyCheckinInterval);
            await triggerMissedCheckinAlert();
        }
    }, 1000);
}

async function triggerMissedCheckinAlert() {
    alert("⚠️ SAFETY CHECK-IN TIMER EXPIRED!\n\nNo check-in received. Triggering automatic emergency SOS alert!");
    try {
        let lat = null;
        let lng = null;
        if (navigator.geolocation) {
            try {
                const pos = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 3000 });
                });
                lat = pos.coords.latitude;
                lng = pos.coords.longitude;
            } catch (e) {
                // proceed without GPS
            }
        }

        const res = await fetch("/api/safety-checkin/trigger-expired", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latitude: lat, longitude: lng })
        });
        const data = await res.json();
        if (res.ok) {
            alert(`🚨 EMERGENCY ACTIVATED FROM MISSED CHECK-IN!\n\nAlert Event #${data.event_id} dispatched to guardians.`);
            resetCheckinUI();
            loadHistory();
        }
    } catch (err) {
        console.error("Expired checkin error:", err);
    }
}

function resetCheckinUI() {
    if (safetyCheckinInterval) clearInterval(safetyCheckinInterval);
    const setupBox = document.getElementById("checkinSetupBox");
    const activeBox = document.getElementById("checkinActiveBox");
    const badge = document.getElementById("checkinStatusBadge");

    if (setupBox) setupBox.classList.remove("hidden");
    if (activeBox) activeBox.classList.add("hidden");
    if (badge) {
        badge.className = "sensor-badge standby";
        badge.textContent = "Standby";
    }
}

document.getElementById("btnStartCheckin")?.addEventListener("click", async () => {
    const duration = document.getElementById("checkinDuration")?.value || 15;
    const note = document.getElementById("checkinNote")?.value || "";

    try {
        const res = await fetch("/api/safety-checkin/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ duration_minutes: parseInt(duration, 10), note })
        });
        const data = await res.json();
        if (res.ok) {
            showActiveCheckinUI(data.checkin, parseInt(duration, 10) * 60);
            alert(`⏱️ Safety Timer Activated for ${duration} minutes!\n\nRemember to tap "I Am Safe" when you reach your destination.`);
        } else {
            alert(data.message || "Failed to start timer.");
        }
    } catch (err) {
        console.error("Start checkin error:", err);
    }
});

document.getElementById("btnConfirmSafe")?.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/safety-checkin/checkin", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (res.ok) {
            resetCheckinUI();
            alert("✅ CHECK-IN CONFIRMED!\n\nYou are safely recorded as arrived. Timer stopped.");
        }
    } catch (err) {
        console.error("Confirm checkin error:", err);
    }
});

document.getElementById("btnCancelCheckin")?.addEventListener("click", () => {
    if (confirm("Cancel this safety check-in timer?")) {
        resetCheckinUI();
    }
});


/* ============================================================
   PHASE 6: NEARBY EMERGENCY SERVICES & HELPLINES
   ============================================================ */

function initNearbyServices() {
    document.getElementById("btnNearbyHospitals")?.addEventListener("click", () => {
        if (userLocation?.latitude && userLocation?.longitude) {
            window.open(`https://www.google.com/maps/search/hospital/@${userLocation.latitude},${userLocation.longitude},14z`, "_blank");
        } else {
            window.open("https://www.google.com/maps/search/hospital", "_blank");
        }
    });

    document.getElementById("btnNearbyPolice")?.addEventListener("click", () => {
        if (userLocation?.latitude && userLocation?.longitude) {
            window.open(`https://www.google.com/maps/search/police+station/@${userLocation.latitude},${userLocation.longitude},14z`, "_blank");
        } else {
            window.open("https://www.google.com/maps/search/police+station", "_blank");
        }
    });
}

initNearbyServices();
setTimeout(() => initSafetyCheckin(), 1000);

/* ============================================================
   UPPER DASHBOARD TAB NAVIGATION & CLASSY VIEW SWITCHER
   ============================================================ */

let sirenOsc1 = null;
let sirenInterval = null;
let sirenGain = null;

function startSirenSound() {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === "suspended") {
            audioCtx.resume();
        }
        stopSirenSound();

        sirenOsc1 = audioCtx.createOscillator();
        sirenGain = audioCtx.createGain();
        sirenOsc1.type = "sawtooth";
        sirenGain.gain.setValueAtTime(0.25, audioCtx.currentTime);

        let freqHigh = true;
        sirenOsc1.frequency.setValueAtTime(960, audioCtx.currentTime);
        sirenOsc1.connect(sirenGain);
        sirenGain.connect(audioCtx.destination);
        sirenOsc1.start();

        sirenInterval = setInterval(() => {
            if (!sirenOsc1 || !audioCtx) return;
            const targetFreq = freqHigh ? 650 : 960;
            sirenOsc1.frequency.exponentialRampToValueAtTime(targetFreq, audioCtx.currentTime + 0.35);
            freqHigh = !freqHigh;
        }, 380);

        document.getElementById("btnPlaySiren")?.classList.add("hidden");
        document.getElementById("btnStopSiren")?.classList.remove("hidden");
    } catch (e) {
        console.warn("Could not start siren audio:", e);
    }
}

function stopSirenSound() {
    if (sirenInterval) {
        clearInterval(sirenInterval);
        sirenInterval = null;
    }
    if (sirenOsc1) {
        try {
            sirenOsc1.stop();
            sirenOsc1.disconnect();
        } catch (e) {}
        sirenOsc1 = null;
    }
    document.getElementById("btnPlaySiren")?.classList.remove("hidden");
    document.getElementById("btnStopSiren")?.classList.add("hidden");
}

function switchDashboardTab(tabId) {
    if (!tabId) return;

    const tabButtons = document.querySelectorAll(".dashboard-tabs .tab-btn");
    const tabPanels = document.querySelectorAll(".tab-content");

    tabButtons.forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    tabPanels.forEach(panel => {
        if (panel.id === tabId) {
            panel.classList.remove("hidden");
        } else {
            panel.classList.add("hidden");
        }
    });

    // Auto-refresh contacts or history when entering those dashboards
    if (tabId === "tabGuardians") {
        loadContacts();
    } else if (tabId === "tabHistory") {
        loadHistory();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

window.switchDashboardTab = switchDashboardTab;

function setupDashboardTabs() {
    const tabButtons = document.querySelectorAll(".dashboard-tabs .tab-btn");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            if (targetId) {
                switchDashboardTab(targetId);
            }
        });
    });

    // Topbar Quick SOS button triggers the main SOS emergency button
    document.getElementById("topbarSosButton")?.addEventListener("click", () => {
        const mainSos = document.getElementById("sosButton");
        if (mainSos) mainSos.click();
    });

    // History refresh button
    document.getElementById("btnRefreshHistory")?.addEventListener("click", () => {
        loadHistory();
    });

    // Siren alarm buttons
    document.getElementById("btnPlaySiren")?.addEventListener("click", startSirenSound);
    document.getElementById("btnStopSiren")?.addEventListener("click", stopSirenSound);

    // Auto-escalation toggle (Single alert mode vs repeat alerts)
    const toggleEscalation = document.getElementById("toggleAutoEscalation");
    const descElem = document.getElementById("escalationSettingDesc");

    function updateEscalationDesc(enabled) {
        if (!descElem) return;
        if (enabled) {
            descElem.innerHTML = `Currently: <b style="color: #2563eb;">Enabled (Auto-Escalation Active)</b>. If an emergency alert is not acknowledged within 60s, SOS Guardian automatically dispatches follow-up alerts to Tier 2 and Tier 3 contacts.`;
        } else {
            descElem.innerHTML = `Currently: <b style="color: #16a34a;">Disabled (Single Alert Mode)</b>. When disabled, SOS Guardian dispatches <b>exactly ONE urgent SMS with Google Maps pin</b> to primary guardians. No repeat messages or follow-up texts will be sent.`;
        }
    }

    if (toggleEscalation) {
        const saved = localStorage.getItem("sos_auto_escalation");
        const isEnabled = (saved === "true");
        toggleEscalation.checked = isEnabled;
        updateEscalationDesc(isEnabled);

        toggleEscalation.addEventListener("change", () => {
            const val = toggleEscalation.checked;
            localStorage.setItem("sos_auto_escalation", val ? "true" : "false");
            updateEscalationDesc(val);
        });
    }
}

// Initialize tabs on startup
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupDashboardTabs);
} else {
    setupDashboardTabs();
}
