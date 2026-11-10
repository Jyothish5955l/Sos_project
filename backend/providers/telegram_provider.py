"""
SOS Guardian - Telegram Bot API Notification Provider
Dispatches emergency alerts via Telegram Bot API with markdown/HTML formatting.
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error


class TelegramProvider:
    """
    Dispatches emergency notifications to Telegram recipients.
    Uses official Telegram Bot API (sendMessage).
    """

    def __init__(self, token=None):
        self.token = (
            token or
            os.getenv("TELEGRAM_BOT_TOKEN", "")
        ).strip()

    def is_configured(self):
        """Returns True if a non-placeholder bot token is present."""
        return bool(
            self.token and
            not self.token.startswith("YOUR_") and
            self.token != "test_token"
        )

    def send_message(self, chat_id, text, parse_mode="HTML"):
        """
        Send a notification to a specific Telegram chat ID.
        Returns a dictionary with status, provider, and error details.
        """
        if not chat_id:
            return {
                "success": False,
                "provider": "telegram",
                "status": "failed",
                "error": "Recipient telegram_chat_id is missing or empty"
            }

        chat_id_str = str(chat_id).strip()

        # If bot token is not configured, run in explicit simulated mode
        if not self.is_configured():
            print("\n✈️ TELEGRAM NOTIFICATION (Simulated - Token not configured)")
            print("--------------------------------------------------")
            print(f"To Chat ID : {chat_id_str}")
            print(f"Parse Mode : {parse_mode}")
            print("Message Content:")
            print(text)
            print("--------------------------------------------------\n")

            return {
                "success": True,
                "provider": "telegram",
                "status": "simulated",
                "chat_id": chat_id_str,
                "note": "Simulated dispatch. Set TELEGRAM_BOT_TOKEN in .env for live alerts."
            }

        api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": chat_id_str,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            api_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SOS-Guardian-Bot/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))

                if response_data.get("ok"):
                    msg_id = response_data.get("result", {}).get("message_id")
                    print(f"✈️ Telegram alert delivered to {chat_id_str} (msg_id: {msg_id})")
                    return {
                        "success": True,
                        "provider": "telegram",
                        "status": "sent",
                        "chat_id": chat_id_str,
                        "message_id": msg_id
                    }
                else:
                    err_desc = response_data.get("description", "Unknown Telegram error")
                    print(f"⚠️ Telegram API error: {err_desc}")
                    return {
                        "success": False,
                        "provider": "telegram",
                        "status": "failed",
                        "chat_id": chat_id_str,
                        "error": err_desc
                    }

        except urllib.error.HTTPError as error:
            error_body = ""
            try:
                error_body = error.read().decode("utf-8", errors="ignore")
                parsed = json.loads(error_body)
                error_desc = parsed.get("description", str(error))
            except Exception:
                error_desc = f"HTTP {error.code}: {error.reason}"

            print(f"⚠️ Telegram HTTPError ({error.code}): {error_desc}")

            # Specific hints for common Telegram Bot API errors
            error_hint = error_desc
            if error.code == 400 and ("chat not found" in error_desc.lower() or "bot was blocked" in error_desc.lower()):
                error_hint = f"{error_desc} (User must start the bot first with /start)"
            elif error.code == 401:
                error_hint = "Invalid TELEGRAM_BOT_TOKEN provided."

            return {
                "success": False,
                "provider": "telegram",
                "status": "failed",
                "chat_id": chat_id_str,
                "error": error_hint,
                "http_code": error.code
            }

        except urllib.error.URLError as error:
            print(f"⚠️ Telegram URLError: {error.reason}")
            return {
                "success": False,
                "provider": "telegram",
                "status": "failed",
                "chat_id": chat_id_str,
                "error": f"Network connection failed: {error.reason}"
            }

        except Exception as error:
            print(f"⚠️ Telegram Unexpected Error: {error}")
            return {
                "success": False,
                "provider": "telegram",
                "status": "failed",
                "chat_id": chat_id_str,
                "error": str(error)
            }

    @staticmethod
    def format_emergency_message(user_name, trigger_type, latitude, longitude, maps_url):
        """Format an emergency distress message with HTML formatting."""
        trigger_display = {
            "manual": "🔴 Manual SOS Button",
            "hand_gesture": "✋ Open-Palm Hand Gesture",
            "voice": "🎤 Voice Command"
        }.get(trigger_type, f"⚡ {trigger_type.upper()}")

        if maps_url and latitude is not None and longitude is not None:
            location_block = (
                f'<b>📍 Emergency Location:</b>\n'
                f'<a href="{maps_url}">🗺️ Open in Google Maps</a>\n'
                f'<code>Coordinates: {latitude}, {longitude}</code>'
            )
        else:
            location_block = (
                f'<b>📍 Emergency Location:</b>\n'
                f'<i>⚠️ Location unavailable (GPS disabled or signal lost)</i>'
            )

        return (
            f"🚨 <b>SOS EMERGENCY ALERT!</b>\n\n"
            f"<b>Distress Signal From:</b> {user_name}\n"
            f"<b>Trigger Modality:</b> {trigger_display}\n\n"
            f"{location_block}\n\n"
            f"⚠️ <b>Action Required:</b> Please check on this person immediately or contact emergency responders!"
        )

    @staticmethod
    def format_test_message(user_name):
        """Format a test notification to verify recipient configuration."""
        return (
            f"🧪 <b>SOS GUARDIAN TEST NOTIFICATION</b>\n\n"
            f"Hello! This is a test alert requested by <b>{user_name}</b> via SOS Guardian.\n\n"
            f"✅ Your Telegram Chat ID is configured properly and will receive alerts in an emergency.\n"
            f"<i>No action is needed.</i>"
        )


telegram_provider = TelegramProvider()
