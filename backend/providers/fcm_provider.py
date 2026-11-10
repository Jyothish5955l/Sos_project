"""
SOS Guardian - Firebase Cloud Messaging (FCM) Provider
Dispatches web push notifications to registered device tokens.
"""

import os
import json
import urllib.request
import urllib.error


class FCMProvider:
    """
    Firebase Cloud Messaging provider.
    Dispatches push notifications to browser and mobile device tokens.
    """

    def __init__(self, server_key=None):
        self.server_key = (
            server_key or
            os.getenv("FCM_SERVER_KEY", "")
        ).strip()

    def is_configured(self):
        return bool(
            self.server_key and
            not self.server_key.startswith("YOUR_")
        )

    def send_push(self, device_token, title, message, data=None):
        """
        Send a push notification to a registered device token.
        """
        if not device_token:
            return {
                "success": False,
                "provider": "fcm",
                "status": "failed",
                "error": "Device token is required"
            }

        token_str = str(device_token).strip()

        if not self.is_configured():
            print("\n🔔 SIMULATED FCM PUSH NOTIFICATION")
            print("--------------------------------")
            print(f"Device Token : {token_str}")
            print(f"Title        : {title}")
            print(f"Message      : {message}")
            print(f"Data         : {data}")
            print("--------------------------------\n")

            return {
                "success": True,
                "provider": "fcm",
                "status": "simulated",
                "device_token": token_str,
                "note": "Simulated dispatch. Set FCM_SERVER_KEY in .env for live push."
            }

        url = "https://fcm.googleapis.com/fcm/send"

        payload = {
            "to": token_str,
            "notification": {
                "title": title,
                "body": message,
                "icon": "/static/icon.png",
                "click_action": "/"
            },
            "data": data or {}
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("success", 0) > 0:
                    print(f"🔔 FCM push sent to {token_str[:12]}...")
                    return {
                        "success": True,
                        "provider": "fcm",
                        "status": "sent",
                        "device_token": token_str
                    }
                else:
                    err_msg = "FCM delivery rejected"
                    results = result.get("results", [])
                    if results and "error" in results[0]:
                        err_msg = results[0]["error"]
                    print(f"⚠️ FCM Error: {err_msg}")
                    return {
                        "success": False,
                        "provider": "fcm",
                        "status": "failed",
                        "device_token": token_str,
                        "error": err_msg
                    }

        except Exception as error:
            print(f"⚠️ FCM Exception: {error}")
            return {
                "success": False,
                "provider": "fcm",
                "status": "failed",
                "device_token": token_str,
                "error": str(error)
            }


fcm_provider = FCMProvider()
