/**
 * SOS Guardian - Voice Recognition Regex & False-Positive Tests
 * Phase 3 Automated Verification
 */

const assert = require("assert");

const EMERGENCY_VOICE_REGEX =
    /\b(sos|help\s+me|i\s+need\s+help|please\s+help|emergency|save\s+me|call\s+for\s+help|sos\s+guardian)\b/i;

function detectEmergencyPhrase(transcript) {
    if (!transcript || typeof transcript !== "string") return null;
    const match = transcript.match(EMERGENCY_VOICE_REGEX);
    return match ? match[0].toLowerCase() : null;
}

console.log("Running Voice SOS Pattern Matching Tests...\n");

// 1. Positive Tests (Must detect)
const positiveCases = [
    { input: "sos", expected: "sos" },
    { input: "SOS", expected: "sos" },
    { input: "Send SOS immediately!", expected: "sos" },
    { input: "help me", expected: "help me" },
    { input: "Help me please, I am trapped", expected: "help me" },
    { input: "I need help right now", expected: "i need help" },
    { input: "Please help, someone is following me", expected: "please help" },
    { input: "emergency", expected: "emergency" },
    { input: "This is a medical emergency!", expected: "emergency" },
    { input: "EMERGENCY CALL", expected: "emergency" },
    { input: "save me", expected: "save me" },
    { input: "Save me, hurry!", expected: "save me" },
    { input: "call for help", expected: "call for help" },
    { input: "sos guardian activate", expected: "sos" } // matches "sos" or "sos guardian"
];

let positivePassCount = 0;
positiveCases.forEach(({ input, expected }, idx) => {
    const detected = detectEmergencyPhrase(input);
    assert(detected !== null, `Positive Case #${idx + 1} Failed: "${input}" should be detected.`);
    positivePassCount++;
    console.log(`  [PASS] Positive #${idx + 1}: "${input}" -> detected "${detected}"`);
});

// 2. Negative Tests / False Positive Mitigation (Must NOT detect)
const negativeCases = [
    "I would like an espresso please",
    "The building had asbestos in the walls",
    "The cherry blossoms are blooming today",
    "Calculate the angle of an isosceles triangle",
    "Meteors burn up in the mesosphere",
    "Emerging market trends in 2026",
    "He provided very helpful feedback on the report",
    "I am going to the season finale tonight",
    "She works at an associated firm",
    "Let's play some soccer after class",
    "Good morning everyone, welcome to the presentation",
    "Can you call me later tonight?",
    "Everything is completely fine and safe"
];

let negativePassCount = 0;
negativeCases.forEach((input, idx) => {
    const detected = detectEmergencyPhrase(input);
    assert(detected === null, `Negative Case #${idx + 1} Failed: "${input}" triggered false positive: "${detected}"`);
    negativePassCount++;
    console.log(`  [PASS] Negative #${idx + 1} (False-Positive Guard): "${input}" -> correctly ignored.`);
});

console.log(`\n========================================`);
console.log(`Voice SOS Pattern Tests Complete!`);
console.log(`Positive Tests Passed: ${positivePassCount} / ${positiveCases.length}`);
console.log(`False Positive Tests Passed: ${negativePassCount} / ${negativeCases.length}`);
console.log(`All ${positivePassCount + negativePassCount} tests PASSED!`);
console.log(`========================================\n`);
