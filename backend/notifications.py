class NotificationService:
    """
    Handles emergency notifications.

    The actual SMS provider will be connected later.
    """

    def send_sms(self, phone, message):

        print("\n📱 SMS NOTIFICATION")
        print("----------------------------")
        print(f"To      : {phone}")
        print(f"Message : {message}")
        print("----------------------------\n")

        # Temporary mock response.
        # Later this will call the selected SMS provider.

        return {
            "success": True,
            "provider": "mock",
            "phone": phone
        }


notification_service = NotificationService()