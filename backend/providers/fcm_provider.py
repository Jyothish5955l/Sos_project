class FCMProvider:
    """
    Firebase Cloud Messaging provider.

    This is the provider interface for push notifications.
    Firebase credentials will be connected later.
    """

    def send_push(self, device_token, title, message, data=None):

        if not device_token:
            return {
                "success": False,
                "provider": "fcm",
                "message": "Device token is required"
            }

        print("\n🔔 FCM PUSH NOTIFICATION")
        print("--------------------------------")
        print(f"Device Token : {device_token}")
        print(f"Title        : {title}")
        print(f"Message      : {message}")
        print(f"Data         : {data}")
        print("--------------------------------\n")

        # Real Firebase API call will be implemented later.

        return {
            "success": True,
            "provider": "fcm",
            "device_token": device_token
        }


fcm_provider = FCMProvider()