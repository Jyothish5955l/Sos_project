"""
SOS Guardian - Modular SMS Notification Provider
Supports Mock simulation, Twilio, and Fast2SMS with provider-independent interfaces.
"""

import os
import json
import re
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
            "note": "Simulated dispatch. Configure httpSMS, Fast2SMS, or Twilio in .env for live carrier delivery."
        }


class TwilioSMSProvider(BaseSMSProvider):
    """
    Twilio SMS provider for live cellular dispatch.
    Configured via TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER.
    """

    name = "twilio"

    def __init__(self, account_sid=None, auth_token=None, from_number=None):
        self.account_sid = (
            account_sid if account_sid is not None else os.getenv("TWILIO_ACCOUNT_SID", "")
        ).strip()
        self.auth_token = (
            auth_token if auth_token is not None else os.getenv("TWILIO_AUTH_TOKEN", "")
        ).strip()
        self.from_number = (
            from_number if from_number is not None else os.getenv("TWILIO_FROM_NUMBER", "")
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
    Fast2SMS provider for live SMS dispatch in supported regions (India).
    Uses Quick SMS route ("q") to utilize free trial signup credits.
    Configured via FAST2SMS_API_KEY.
    """

    name = "fast2sms"

    def __init__(self, api_key=None):
        self.api_key = (
            api_key if api_key is not None else os.getenv("FAST2SMS_API_KEY", "")
        ).strip()

    def is_configured(self):
        return bool(
            self.api_key and
            not self.api_key.startswith("YOUR_")
        )

    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """
        Sanitize phone number for Fast2SMS Quick SMS route.
        Fast2SMS expects a 10-digit Indian mobile number.
        Strips country codes (+91, 91) or leading 0 if present.
        """
        digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
        if len(digits) == 12 and digits.startswith("91"):
            return digits[2:]
        if len(digits) == 11 and digits.startswith("0"):
            return digits[1:]
        return digits

    def send_sms(self, phone: str, message: str) -> dict:
        phone_str = str(phone).strip()
        clean_phone = self.clean_phone_number(phone_str)

        if not self.is_configured():
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": phone_str,
                "error": "Fast2SMS API key unconfigured (set FAST2SMS_API_KEY in .env)"
            }

        if len(clean_phone) != 10:
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": phone_str,
                "error": f"Invalid mobile number format for Fast2SMS (requires 10 digits, got '{phone_str}')"
            }

        url = "https://www.fast2sms.com/dev/bulkV2"

        # Fast2SMS Quick SMS route ("q") utilizes free trial signup credits
        payload = {
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": clean_phone
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "authorization": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "SOS-Guardian-Fast2SMS/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("return"):
                    print(f"📱 Fast2SMS alert dispatched to {clean_phone} via Quick route ('q')")
                    return {
                        "success": True,
                        "provider": "fast2sms",
                        "status": "sent",
                        "phone": clean_phone,
                        "request_id": result.get("request_id"),
                        "message": result.get("message")
                    }
                else:
                    raw_msg = result.get("message", "Failed")
                    err_msg = ", ".join(raw_msg) if isinstance(raw_msg, list) else str(raw_msg)
                    print(f"⚠️ Fast2SMS Error: {err_msg}")
                    return {
                        "success": False,
                        "provider": "fast2sms",
                        "status": "failed",
                        "phone": clean_phone,
                        "error": str(err_msg)
                    }

        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(error_body)
                raw_msg = parsed.get("message", str(error))
                err_msg = ", ".join(raw_msg) if isinstance(raw_msg, list) else str(raw_msg)
            except Exception:
                err_msg = f"HTTP {error.code}: {error.reason}"

            print(f"⚠️ Fast2SMS HTTP Error ({error.code}): {err_msg}")
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": clean_phone,
                "error": err_msg,
                "http_code": error.code
            }

        except urllib.error.URLError as error:
            print(f"⚠️ Fast2SMS URLError: {error.reason}")
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": clean_phone,
                "error": f"Network error: {error.reason}"
            }

        except Exception as error:
            print(f"⚠️ Fast2SMS Exception: {error}")
            return {
                "success": False,
                "provider": "fast2sms",
                "status": "failed",
                "phone": clean_phone,
                "error": str(error)
            }


class HttpSMSProvider(BaseSMSProvider):
    """
    httpSMS provider for cellular text message dispatch via an Android phone gateway.
    API: https://api.httpsms.com/v1/messages/send
    Configured via HTTPSMS_API_KEY and HTTPSMS_FROM_NUMBER.
    """

    name = "httpsms"

    def __init__(self, api_key=None, from_number=None):
        self.api_key = (
            api_key if api_key is not None else os.getenv("HTTPSMS_API_KEY", "")
        ).strip()
        self.from_number = (
            from_number if from_number is not None else os.getenv("HTTPSMS_FROM_NUMBER", "")
        ).strip()

    def is_configured(self):
        return bool(
            self.api_key and
            self.from_number and
            not self.api_key.startswith("YOUR_") and
            not self.from_number.startswith("YOUR_")
        )

    @staticmethod
    def format_e164(phone: str, default_country_code: str = "+91") -> str:
        """
        Format destination phone number to standard E.164.
        Ensures destination phone numbers are formatted in standard E.164
        (e.g., adding +91 prefix for 10-digit Indian numbers if missing).
        """
        raw = str(phone or "").strip()
        if raw.startswith("+"):
            digits_only = "".join(ch for ch in raw if ch.isdigit())
            return f"+{digits_only}"

        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) == 10:
            return f"{default_country_code}{digits}"
        elif len(digits) == 11 and digits.startswith("0"):
            return f"{default_country_code}{digits[1:]}"
        elif len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
        elif len(digits) > 7:
            return f"+{digits}"
        return raw

    def send_sms(self, phone: str, message: str) -> dict:
        phone_str = str(phone).strip()
        to_number = self.format_e164(phone_str)
        from_number = self.format_e164(self.from_number)

        if not self.is_configured():
            return {
                "success": False,
                "provider": "httpsms",
                "status": "failed",
                "phone": to_number,
                "error": "httpSMS credentials unconfigured (set HTTPSMS_API_KEY and HTTPSMS_FROM_NUMBER in .env)"
            }

        url = "https://api.httpsms.com/v1/messages/send"
        payload = {
            "content": message,
            "from": from_number,
            "to": to_number
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "SOS-Guardian-HttpSMS/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_text = response.read().decode("utf-8")
                result = json.loads(resp_text) if resp_text else {}
                msg_id = result.get("id") or (result.get("data", {}).get("id") if isinstance(result.get("data"), dict) else None)
                print(f"📱 httpSMS alert dispatched to {to_number} (ID: {msg_id})")
                return {
                    "success": True,
                    "provider": "httpsms",
                    "status": "sent",
                    "phone": to_number,
                    "message_id": msg_id,
                    "response": result
                }
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(error_body)
                err_msg = parsed.get("message") or parsed.get("error") or str(error)
            except Exception:
                err_msg = f"HTTP {error.code}: {error.reason}"

            if error.code == 401:
                err_msg = (
                    f"401 Unauthorized: {err_msg} - "
                    "Make sure you use the Account API Key from https://httpsms.com/settings. "
                    "Keys starting with 'pk_' are Phone API Keys used only for logging into the Android app."
                )

            print(f"⚠️ httpSMS HTTP Error ({error.code}): {err_msg}")
            return {
                "success": False,
                "provider": "httpsms",
                "status": "failed",
                "phone": to_number,
                "error": err_msg,
                "http_code": error.code
            }
        except urllib.error.URLError as error:
            print(f"⚠️ httpSMS URLError: {error.reason}")
            return {
                "success": False,
                "provider": "httpsms",
                "status": "failed",
                "phone": to_number,
                "error": f"Network error: {error.reason}"
            }
        except Exception as error:
            print(f"⚠️ httpSMS Exception: {error}")
            return {
                "success": False,
                "provider": "httpsms",
                "status": "failed",
                "phone": to_number,
                "error": str(error)
            }


def get_sms_provider(provider_name=None) -> BaseSMSProvider:
    """
    Factory function resolving active SMS provider from environment or argument.
    Defaults to MockSMSProvider if credentials are not configured or SMS_PROVIDER=mock.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

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

    elif selected == "httpsms":
        provider = HttpSMSProvider()
        if provider.is_configured():
            return provider
        print("⚠️ httpSMS selected as SMS_PROVIDER but credentials missing. Falling back to mock.")
        return MockSMSProvider()

    return MockSMSProvider()


def format_emergency_sms(user_name, trigger_type, maps_url=None, latitude=None, longitude=None):
    """
    Format emergency text message for standard cellular SMS.
    Includes clickable Google Maps pin: https://www.google.com/maps?q=LAT,LONG
    or explicitly displays 'GPS Unavailable' when location coordinates are missing.
    """
    if latitude is not None and longitude is not None:
        pin_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        loc_text = f"📍 Location:\n{pin_url}"
    elif maps_url:
        loc_text = f"📍 Location:\n{maps_url}"
    else:
        loc_text = "📍 Location: GPS Unavailable"

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

