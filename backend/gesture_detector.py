# ============================================================
# SOS GUARDIAN - HAND GESTURE DETECTOR
# ============================================================

import cv2
import mediapipe as mp
import numpy as np


# ============================================================
# MEDIAPIPE SETUP
# ============================================================

mp_hands = mp.solutions.hands

hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.55,
    min_tracking_confidence=0.55
)


# ============================================================
# DISTANCE
# ============================================================

def distance(point1, point2):

    return np.sqrt(
        (point1.x - point2.x) ** 2 +
        (point1.y - point2.y) ** 2 +
        (point1.z - point2.z) ** 2
    )


# ============================================================
# OPEN PALM DETECTION
# ============================================================

def is_open_palm(landmarks):

    wrist = landmarks[0]

    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]

    index_tip = landmarks[8]
    index_pip = landmarks[6]

    middle_tip = landmarks[12]
    middle_pip = landmarks[10]

    ring_tip = landmarks[16]
    ring_pip = landmarks[14]

    pinky_tip = landmarks[20]
    pinky_pip = landmarks[18]


    # --------------------------------------------------------
    # Finger extension
    # --------------------------------------------------------

    index_open = (
        distance(index_tip, wrist)
        >
        distance(index_pip, wrist) * 1.08
    )

    middle_open = (
        distance(middle_tip, wrist)
        >
        distance(middle_pip, wrist) * 1.08
    )

    ring_open = (
        distance(ring_tip, wrist)
        >
        distance(ring_pip, wrist) * 1.08
    )

    pinky_open = (
        distance(pinky_tip, wrist)
        >
        distance(pinky_pip, wrist) * 1.08
    )


    # --------------------------------------------------------
    # Thumb
    # --------------------------------------------------------

    thumb_open = (
        distance(thumb_tip, pinky_pip)
        >
        distance(thumb_ip, pinky_pip) * 1.03
    )


    # --------------------------------------------------------
    # Open palm
    # --------------------------------------------------------

    return (
        index_open
        and middle_open
        and ring_open
        and pinky_open
        and thumb_open
    )


# ============================================================
# DETECT HAND
# ============================================================

def detect_hand(image_bytes):

    try:

        # ----------------------------------------------------
        # Convert bytes → numpy array
        # ----------------------------------------------------

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8
        )

        # ----------------------------------------------------
        # Decode image
        # ----------------------------------------------------

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if image is None:

            return {
                "success": False,
                "hand_detected": False,
                "open_palm": False,
                "gesture": "none",
                "message": "Invalid image"
            }


        # ----------------------------------------------------
        # BGR → RGB
        # ----------------------------------------------------

        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )


        # ----------------------------------------------------
        # MediaPipe
        # ----------------------------------------------------

        result = hands.process(
            rgb_image
        )


        # ----------------------------------------------------
        # No hand
        # ----------------------------------------------------

        if not result.multi_hand_landmarks:

            return {
                "success": True,
                "hand_detected": False,
                "open_palm": False,
                "gesture": "none",
                "message": "No hand detected"
            }


        # ----------------------------------------------------
        # First hand
        # ----------------------------------------------------

        landmarks = (
            result
            .multi_hand_landmarks[0]
            .landmark
        )


        # ----------------------------------------------------
        # Check open palm
        # ----------------------------------------------------

        open_palm = is_open_palm(
            landmarks
        )


        if open_palm:

            return {
                "success": True,
                "hand_detected": True,
                "open_palm": True,
                "gesture": "open_palm",
                "message": "Open palm detected"
            }


        return {
            "success": True,
            "hand_detected": True,
            "open_palm": False,
            "gesture": "hand",
            "message": "Hand detected"
        }


    except Exception as error:

        print(
            "Gesture detection error:",
            error
        )

        return {
            "success": False,
            "hand_detected": False,
            "open_palm": False,
            "gesture": "none",
            "message": str(error)
        }