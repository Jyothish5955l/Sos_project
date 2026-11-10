# 🛡️ SOS Guardian — Emergency Assistance & Protection Platform

**SOS Guardian** is a real-time, multi-modal emergency assistance web platform designed for rapid personal distress dispatch. It enables users to trigger life-saving emergency notifications using manual controls, hands-free computer vision, voice recognition, motion shock sensors, or automated safety check-in timers.

---

## 🌟 Key Features

### 🚨 Emergency Command Center
* **Instant Quick SOS**: One-tap emergency activation immediately broadcasts your distress status.
* **Live GPS Geolocation Streaming**: Captures real-time coordinates and generates clickable Google Maps links (`https://www.google.com/maps?q=LAT,LNG`).
* **Interactive Active Tracker**: Live status hub showing responders, GPS breadcrumbs, escalation status, and trail mapping during an active emergency.
* **National Helplines**: One-tap direct dial for Police (112), Ambulance (108), Women Helpline (1091), and Fire Service (101).

### 👥 Multi-Tier Guardian Escalation System
* **Tier 1 — Primary (Immediate Alert)**: Immediate family (Mom, Dad, Spouse) notified instantly on any trigger.
* **Tier 2 — Secondary (Escalation Alert)**: Close friends or neighbors notified after 60 seconds if unacknowledged, or upon manual escalation.
* **Tier 3 — Backup (Critical Escalation)**: Extended emergency network or doctors for severe situations.
* **Flexible Dispatch Modes**:
  * *Single Alert Mode*: Dispatches exactly ONE urgent SMS with Google Maps pin to primary guardians.
  * *Auto-Escalation Mode*: Automatically cascades to Tier 2 and Tier 3 if an alert is not acknowledged within 60 seconds.

### ✋ AI Sensor Hub
* **Gesture Guardian**: Open-palm hands-free emergency trigger powered by client-side MediaPipe hand tracking (no video is transmitted to the server).
* **Voice SOS Engine**: Continuous hands-free voice recognition detecting distress phrases (*"SOS"*, *"Help me"*, *"Emergency"*) via Web Speech API.
* **Intelligent Fall Detection**: Device motion and acceleration spike analysis with an audible 15-second safety countdown prompt to avoid false alarms.

### ⏱️ Personal Safety Tools
* **Safety Check-in Timer (Dead-Man's Switch)**: Set a timer with a destination note (e.g. *"Walking home from metro"*). If you do not check in before expiration, an emergency alert is automatically dispatched.
* **Emergency Service Locator**: Instant GPS lookup for nearby hospitals and police stations.

### 📱 Notification Channels
* **Direct Cellular SMS Gateway (httpSMS)**: Dispatches carrier SMS directly through an Android SIM gateway without third-party aggregator costs or delays.
* **Telegram Messenger Bot**: High-speed backup alerts delivered directly to Telegram handles or group chats.
* **Emergency Acoustic Siren**: Browser-synthesized 90dB warble alarm (650Hz–960Hz) to deter attackers and attract immediate nearby attention.

---

## 🛠️ Technology Stack

* **Backend**: Python 3.11, Flask, SQLite 3 (Write-Ahead Logging / WAL mode), Gunicorn / Waitress WSGI
* **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 Glassmorphism UI
* **Vision & Audio**: MediaPipe Hands, Web Speech API, Web Audio API
* **Deployment**: Docker, Render, Railway, Linux VPS

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the Repository
```bash
git clone https://github.com/Jyothish5955l/Sos_project.git
cd Sos_project
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your credentials:
```dotenv
FLASK_SECRET_KEY=your_secret_key_here
SMS_PROVIDER=httpsms
HTTPSMS_API_KEY=your_httpsms_account_api_key
HTTPSMS_FROM_NUMBER=+91XXXXXXXXXX
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_optional
```

### 5. Run the Server
```bash
python wsgi.py
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🐳 Docker Deployment

Build and run the production container:
```bash
# Build image
docker build -t sos-guardian .

# Run container
docker run -d -p 5000:5000 --env-file .env --name sos-guardian-app sos-guardian
```

---

## ☁️ Cloud Deployment (Render.com)

1. Connect your repository to **[Render.com](https://render.com)**.
2. Select **Web Service**.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT`
5. Configure your environment variables in the Render dashboard.

---

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
