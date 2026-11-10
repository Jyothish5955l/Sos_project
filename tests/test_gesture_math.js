// Unit tests for gesture recognition math (distance, angle, fingerOpen, thumbOpen, detectOpenPalm)

function distance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    const dz = (a.z || 0) - (b.z || 0);
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function angle(a, b, c) {
    const ab = { x: a.x - b.x, y: a.y - b.y, z: (a.z || 0) - (b.z || 0) };
    const cb = { x: c.x - b.x, y: c.y - b.y, z: (c.z || 0) - (b.z || 0) };
    const dot = ab.x * cb.x + ab.y * cb.y + ab.z * cb.z;
    const ma = Math.sqrt(ab.x ** 2 + ab.y ** 2 + ab.z ** 2);
    const mc = Math.sqrt(cb.x ** 2 + cb.y ** 2 + cb.z ** 2);
    if (!ma || !mc) return 0;
    return Math.acos(Math.max(-1, Math.min(1, dot / (ma * mc)))) * 180 / Math.PI;
}

function fingerOpen(landmarks, mcp, pip, dip, tip) {
    const wrist = landmarks[0];
    const tipDist = distance(landmarks[tip], wrist);
    const pipDist = distance(landmarks[pip], wrist);
    const mcpDist = distance(landmarks[mcp], wrist);
    const isExtended = tipDist > pipDist * 1.05 && pipDist > mcpDist * 0.95;
    const jointAngle = angle(landmarks[pip], landmarks[dip], landmarks[tip]);
    return isExtended && jointAngle > 125;
}

function thumbOpen(landmarks) {
    const wrist = landmarks[0];
    const thumbTip = landmarks[4];
    const thumbIP = landmarks[3];
    const thumbMCP = landmarks[2];
    const indexMCP = landmarks[5];
    const pinkyMCP = landmarks[17];

    const tipToPinky = distance(thumbTip, pinkyMCP);
    const ipToPinky = distance(thumbIP, pinkyMCP);
    const tipToIndex = distance(thumbTip, indexMCP);
    const mcpToIndex = distance(thumbMCP, indexMCP);
    const tipToWrist = distance(thumbTip, wrist);
    const ipToWrist = distance(thumbIP, wrist);

    const isAbducted = tipToPinky > ipToPinky * 0.98;
    const isSeparated = tipToIndex > mcpToIndex * 1.1;
    const isNotCurled = tipToWrist > ipToWrist * 0.95;

    return isAbducted && (isSeparated || isNotCurled);
}

function detectOpenPalm(landmarks) {
    if (!landmarks || landmarks.length !== 21) {
        return { detected: false, fingers: 0, thumb: false };
    }
    const index = fingerOpen(landmarks, 5, 6, 7, 8);
    const middle = fingerOpen(landmarks, 9, 10, 11, 12);
    const ring = fingerOpen(landmarks, 13, 14, 15, 16);
    const pinky = fingerOpen(landmarks, 17, 18, 19, 20);
    const thumb = thumbOpen(landmarks);
    const fingers = [index, middle, ring, pinky].filter(Boolean).length;
    return { detected: fingers === 4 && thumb, fingers, thumb };
}

// -------------------------------------------------------------
// TEST CASES
// -------------------------------------------------------------

console.log("=== Running Gesture Math Unit Tests ===");

// 1. Synthesize Open Palm Landmarks
// Wrist at (0, 0, 0), fingers pointing UP (negative Y), thumb pointing LEFT (negative X)
const openPalm = new Array(21).fill(null).map(() => ({ x: 0, y: 0, z: 0 }));
openPalm[0] = { x: 0.5, y: 0.9, z: 0 }; // Wrist

// Thumb (spread left)
openPalm[1] = { x: 0.45, y: 0.8, z: 0 };
openPalm[2] = { x: 0.38, y: 0.72, z: 0 }; // Thumb MCP
openPalm[3] = { x: 0.30, y: 0.65, z: 0 }; // Thumb IP
openPalm[4] = { x: 0.22, y: 0.60, z: 0 }; // Thumb Tip

// Index (straight up)
openPalm[5] = { x: 0.42, y: 0.60, z: 0 }; // Index MCP
openPalm[6] = { x: 0.40, y: 0.48, z: 0 }; // Index PIP
openPalm[7] = { x: 0.39, y: 0.38, z: 0 }; // Index DIP
openPalm[8] = { x: 0.38, y: 0.28, z: 0 }; // Index Tip

// Middle (straight up)
openPalm[9] = { x: 0.50, y: 0.58, z: 0 };
openPalm[10] = { x: 0.50, y: 0.45, z: 0 };
openPalm[11] = { x: 0.50, y: 0.34, z: 0 };
openPalm[12] = { x: 0.50, y: 0.24, z: 0 };

// Ring (straight up)
openPalm[13] = { x: 0.58, y: 0.60, z: 0 };
openPalm[14] = { x: 0.60, y: 0.48, z: 0 };
openPalm[15] = { x: 0.61, y: 0.38, z: 0 };
openPalm[16] = { x: 0.62, y: 0.28, z: 0 };

// Pinky (straight up)
openPalm[17] = { x: 0.66, y: 0.63, z: 0 }; // Pinky MCP
openPalm[18] = { x: 0.68, y: 0.52, z: 0 };
openPalm[19] = { x: 0.70, y: 0.43, z: 0 };
openPalm[20] = { x: 0.72, y: 0.35, z: 0 };

const openRes = detectOpenPalm(openPalm);
console.log("Test 1 - Open Palm Detection:", openRes);
if (!openRes.detected || openRes.fingers !== 4 || !openRes.thumb) {
    console.error("FAIL: Expected open palm to be detected!");
    process.exit(1);
} else {
    console.log("PASS: Open palm successfully recognized.");
}

// 2. Synthesize Closed Fist Landmarks (fingers curled into palm)
const closedFist = JSON.parse(JSON.stringify(openPalm));
// Curl index, middle, ring, pinky tips back towards wrist/palm
closedFist[8] = { x: 0.42, y: 0.68, z: 0.05 }; // Tip curled below PIP
closedFist[12] = { x: 0.50, y: 0.66, z: 0.05 };
closedFist[16] = { x: 0.58, y: 0.68, z: 0.05 };
closedFist[20] = { x: 0.66, y: 0.70, z: 0.05 };
// Thumb folded over fingers
closedFist[4] = { x: 0.45, y: 0.65, z: 0.08 };

const fistRes = detectOpenPalm(closedFist);
console.log("Test 2 - Closed Fist Detection:", fistRes);
if (fistRes.detected) {
    console.error("FAIL: Closed fist was incorrectly detected as open palm!");
    process.exit(1);
} else {
    console.log("PASS: Closed fist correctly rejected.");
}

// 3. Synthesize Peace / Two Fingers extended
const peaceSign = JSON.parse(JSON.stringify(openPalm));
// Curl ring and pinky
peaceSign[16] = { x: 0.58, y: 0.68, z: 0.05 };
peaceSign[20] = { x: 0.66, y: 0.70, z: 0.05 };

const peaceRes = detectOpenPalm(peaceSign);
console.log("Test 3 - Partial Hand (Peace Sign):", peaceRes);
if (peaceRes.detected) {
    console.error("FAIL: Partial hand was incorrectly detected as open palm!");
    process.exit(1);
} else {
    console.log("PASS: Partial hand correctly rejected.");
}

// 4. Empty/Null array
const emptyRes = detectOpenPalm(null);
console.log("Test 4 - Null Landmark Handling:", emptyRes);
if (emptyRes.detected) {
    console.error("FAIL: Null landmarks produced true detection!");
    process.exit(1);
} else {
    console.log("PASS: Null landmarks handled safely.");
}

console.log("\nALL GESTURE MATH UNIT TESTS PASSED!");
