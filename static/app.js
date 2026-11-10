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
    }


    loadContacts();

    loadHistory();

    startGestureSystem();

    startVoiceSOS();
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
   VOICE SOS
   ============================================================ */

function startVoiceSOS() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;


    if (!SpeechRecognition) {

        console.warn(
            "Speech Recognition is not supported by this browser."
        );


        updateVoiceStatus(
            "Voice SOS not supported in this browser."
        );


        return;
    }


    if (voiceRunning) {

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


                console.log(
                    "🎤 Voice SOS listening..."
                );


                updateVoiceStatus(
                    "🎤 Listening for emergency words..."
                );
            };


        voiceRecognition.onresult =
            event => {

                let transcript =
                    "";


                for (
                    let i =
                        event.resultIndex;

                    i <
                    event.results.length;

                    i++
                ) {

                    transcript +=
                        event.results[i][0]
                            .transcript;
                }


                transcript =
                    transcript
                        .toLowerCase()
                        .trim();


                console.log(
                    "🎤 Heard:",
                    transcript
                );


                checkEmergencyVoice(
                    transcript
                );
            };


        voiceRecognition.onerror =
            event => {

                console.warn(
                    "Voice recognition:",
                    event.error
                );


                voiceRunning =
                    false;


                if (
                    event.error ===
                    "not-allowed"
                ) {

                    updateVoiceStatus(
                        "🎤 Microphone permission denied."
                    );
                }
            };


        voiceRecognition.onend =
            () => {

                voiceRunning =
                    false;


                /*
                   Automatically restart speech
                   recognition if the user is still
                   logged into the dashboard.
                */

                if (
                    currentUser &&
                    dashboard &&
                    !dashboard.classList.contains(
                        "hidden"
                    )
                ) {

                    setTimeout(
                        () => {

                            if (
                                !voiceRunning
                            ) {

                                startVoiceSOS();
                            }

                        },
                        700
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
    }
}


/* ============================================================
   CHECK EMERGENCY VOICE
   ============================================================ */

function checkEmergencyVoice(
    transcript
) {

    if (
        voiceTriggered ||
        countdownTimer
    ) {

        return;
    }


    const emergencyPhrases = [

        "sos",

        "help me",

        "i need help",

        "please help",

        "emergency",

        "save me",

        "call for help",

        "sos guardian"
    ];


    const detected =
        emergencyPhrases.some(
            phrase =>
                transcript.includes(
                    phrase
                )
        );


    if (!detected) {

        return;
    }


    console.log(
        "🚨 EMERGENCY VOICE DETECTED:",
        transcript
    );


    voiceTriggered =
        true;


    updateVoiceStatus(
        "🚨 Emergency voice detected!"
    );


    startSosCountdown(
        "voice"
    );


    setTimeout(
        () => {

            if (
                !countdownTimer
            ) {

                voiceTriggered =
                    false;
            }

        },
        10000
    );
}


/* ============================================================
   VOICE STATUS
   ============================================================ */

function updateVoiceStatus(
    message
) {

    const element =
        document.getElementById(
            "voiceStatus"
        );


    if (element) {

        element.textContent =
            message;
    }
}


/* ============================================================
   STOP VOICE
   ============================================================ */

function stopVoiceSOS() {

    if (
        voiceRecognition
    ) {

        try {

            voiceRecognition.stop();

        } catch (error) {

            console.warn(
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

                            </div>

                            <div class="contact-phone">

                                ${escapeHtml(
                                    contact.phone
                                )}
                                ${contact.telegram_chat_id ? `<br><small style="color:#60a5fa">✈️ ${escapeHtml(contact.telegram_chat_id)}</small>` : ""}

                            </div>

                        </div>


                        <button
                            class="delete-btn"
                            onclick="deleteContact(${contact.id})"
                        >
                            Delete
                        </button>

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
                                    telegram_chat_id
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


        if (response.ok) {

            loadContacts();
        }

    } catch (error) {

        console.error(
            error
        );
    }
}


window.deleteContact =
    deleteContact;


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
                                ${escapeHtml(
                                    event.status
                                )}

                                <br>

                                Location:
                                ${event.latitude},
                                ${event.longitude}

                                <br>

                                ${date}

                            </div>


                            <br>


                            <a
                                href="${event.maps_url}"
                                target="_blank"
                            >
                                📍 Open Location
                            </a>

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