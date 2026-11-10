"""
SOS Guardian - Modular SMS Notification Provider
Supports Mock simulation, Twilio, and Fast2SMS with provider-independent interfaces.
"""

import os
import json
import base64
import urllib.request
import urllib.parse
import urllib.error


class BaseSMSProvider:
    """Abstract base class for all SMS notification providers."""

    name = "base"

    def send_sms(self, phone: str, message: str) -> dict:
        raise NotImplementedError


class MockSMSProvider(BaseSMSProvider):
    """
    Simulated SMS provider for testing and development.
    Outputs cleanly to server console without requiring paid telecom credentials.
    """

    name = "mock"

    def send_sms(self, phone: str, message: str) -> dict:
        phone_str = str(phone).strip()

        print("\n📱 SIMULATED SMS NOTIFICATION")
        print("----------------------------------------")
        print(f"Provider : Mock (Simulated)")
        print(f"To Phone : {phone_str}")
        print("Message  :")
        print(message)
        print("----------------------------------------\n")

        return {
            "success": True,
            "provider": "mock",
            "status": "simulated",
            "phone": phone_str,
            "note": "Simulated dispatch. Configure Twilio or Fast2SMS in .env for live carrier delivery."
        }


class TwilioSMSProvider(BaseSMSProvider):
    """
    Twilio SMS provider for live cellular dispatch.
    Configured via TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER.
    """

    name = "twilio"

    def __init__(self, account_sid=None, auth_token=None, from_number=None):
        self.account_sid = (
            account_sid or
            os.getenv("TWILIO_ACCOUNT_SID", "")
        ).strip()

        self.auth_token = (
            auth_token or
            os.getenv("TWILIO_AUTH_TOKEN", "")
        ).strip()

        self.from_number = (
            from_number or
            os.getenv("TWILIO_FROM_NUMBER", "")
        ).strip()

    def is_configured(self):
        return bool(
            self.account_sid and
            self.auth_token and
            self.from_number and
            not self.account_sid.startswith("YOUR_")
        )

    def send_sms(self, phone: str, message: str) -> dict:
        phone_str = str(phone).strip()

        if not self.is_configured():
            return {
                "success": False,
                "provider": "twilio",
                "status": "failed",
                "phone": phone_str,
                "error": "Twilio credentials incomplete or unconfigured"
            }

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        data = urllib.parse.urlencode({
            "To": phone_str,
            "From": self.from_number,
            "Body": message
        }).encode("utf-8")

        credentials = f"{self.account_sid}:{self.auth_token}"
        auth_header = "Basic " + base64.b64encode(credentials.encode("ascii")).decode("ascii")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "SOS-Guardian-Twilio/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                sid = result.get("sid")
                print(f"📱 Twilio SMS dispatched to {phone_str} (SID: {sid})")
                return {
                    "success": True,
                    "provider": "twilio",
                    "status": "sent",
                    "phone": phone_str,
                    "sid": sid
                }

        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(error_body)
                error_msg = parsed.get("message", str(error))
            except Exception:
                error_msg = f"HTTP {error.code}: {error.reason}"

            print(f"⚠️ Twilio HTTP Error ({error.code}): {error_msg}")
            return {
                "success": False,
                "provider": "twilio",
                "status": "failed",
                "phone": phone_str,
                "error": error_msg,
                "http_code": error.code
            }

        except urllib.error.URLError as error:
            print(f"⚠️ Twilio URLError: {error.reason}")
            return {
                "success": False,
                "provider": "twilio",
                "status": "failed",
                "phone": phone_str,
                "error": f"Network error: {error.reason}"
            }

        except Exception as error:
            print(f"⚠️ Twilio Unexpected Error: {error}")
            return {
                "success": False,
                "provider": "twilio",
                "status": "failed",
                "phone": phone_str,
                "error": str(error)
            }


class Fast2SMSProvider(BaseSMSProvider):
    """
    Fast2SMS provider for live SMS dispatch in supported regions.
    Configured via FAST2SMS_API_KEY.
    """

    name = "fast2sms"

    def __init__(self, api_key=None):
        self.api_key = (
            api_key or
            os.getenv("FAST2SMS_API_KEY", "")
        ).strip()

    def is_configured(self):
        return bool(
            self.api_key and
            not self.api_key.startswith("YOUR_")
        )

    def send_sms(self, phone: str, message: str) -> dict:
        phone_str = str(phone).strip()

        if not self.is_configured():
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": phone_str,
                "error": "Fast2SMS API key unconfigured"
            }

        url = "https://www.fast2sms.com/dev/bulkV2"

        payload = {
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": phone_str
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "authorization": self.api_key,
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("return"):
                    print(f"📱 Fast2SMS alert dispatched to {phone_str}")
                    return {
                        "success": True,
                        "provider": "fast2sms",
                        "status": "sent",
                        "phone": phone_str
                    }
                else:
                    err_msg = result.get("message", ["Unknown error"])[0] if isinstance(result.get("message"), list) else result.get("message", "Failed")
                    print(f"⚠️ Fast2SMS Error: {err_msg}")
                    return {
                        "success": False,
                        "provider": "fast2sms",
                        "status": "failed",
                        "phone": phone_str,
                        "error": str(err_msg)
                    }

        except Exception as error:
            print(f"⚠️ Fast2SMS Exception: {error}")
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": phone_str,
                "error": str(error)
            }


def get_sms_provider(provider_name=None) -> BaseSMSProvider:
    """
    Factory function resolving active SMS provider from environment or argument.
    Defaults to MockSMSProvider if credentials are not configured.
    """
    selected = (
        provider_name or
        os.getenv("SMS_PROVIDER", "mock")
    ).strip().lower()

    if selected == "twilio":
        provider = TwilioSMSProvider()
        if provider.is_configured():
            return provider
        print("⚠️ Twilio selected as SMS_PROVIDER but credentials missing. Falling back to mock.")
        return MockSMSProvider()

    elif selected == "fast2sms":
        provider = Fast2SMSProvider()
        if provider.is_configured():
            return provider
        print("⚠️ Fast2SMS selected as SMS_PROVIDER but API key missing. Falling back to mock.")
        return MockSMSProvider()

    return MockSMSProvider()


def format_emergency_sms(user_name, trigger_type, maps_url):
    """Format emergency text message for standard cellular SMS."""
    loc_text = f"📍 Location:\n{maps_url}" if maps_url else "📍 Location: Unavailable (User GPS disabled or signal lost)"
    return (
        f"🚨 SOS EMERGENCY ALERT!\n\n"
        f"Distress alert activated by {user_name} via {trigger_type}.\n\n"
        f"{loc_text}\n\n"
        f"Please check on this person immediately."
    )


def format_test_sms(user_name):
    """Format verification SMS for emergency contact testing."""
    return (
        f"🧪 SOS Guardian Test\n\n"
        f"Hello! This is a test notification from {user_name} via SOS Guardian to verify your phone number.\n\n"
        f"No action is required."
    )


sms_provider = get_sms_provider()
