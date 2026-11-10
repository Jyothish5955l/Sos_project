"""
SOS Guardian - Multi-Channel Emergency Notification Service
Orchestrates emergency distress dispatches across SMS, Telegram, and Push.
Tracks per-channel delivery results and logs history in SQLite.
"""

from providers.telegram_provider import telegram_provider, TelegramProvider
from providers.sms_provider import (
    get_sms_provider,
    format_emergency_sms,
    format_test_sms,
    Fast2SMSProvider,
    MockSMSProvider,
    TwilioSMSProvider
)
from providers.fcm_provider import fcm_provider
from database import log_notification, update_sos_event_status, get_contacts as db_get_contacts


class NotificationService:
    """
    Central emergency notification orchestrator.
    Handles multichannel dispatch (Telegram, SMS, FCM) with full error recovery,
    per-recipient delivery tracking, and persistent database auditing.
    """

    def __init__(self, custom_sms_provider=None):
        self.telegram = telegram_provider
        self.fcm = fcm_provider
        self._custom_sms = custom_sms_provider

    @property
    def sms(self):
        """Dynamically fetch active SMS provider based on current environment or instance."""
        if self._custom_sms is not None:
            return self._custom_sms
        return get_sms_provider()

    def send_emergency_alerts(
        self,
        sos_event_id,
        user_name,
        trigger_type,
        latitude,
        longitude,
        maps_url,
        contacts=None,
        user_id=None
    ):
        """
        Dispatch emergency alerts to all configured contacts across all active channels.
        Pulls saved numbers from SQLite if contacts list is not explicitly passed.
        Logs every attempt in the database and updates overall SOS event status.
        """
        # Pull saved contacts directly from SQLite if not explicitly passed
        if contacts is None and user_id is not None:
            contacts = db_get_contacts(user_id)
        elif contacts is None:
            contacts = []

        if not contacts:
            if sos_event_id:
                update_sos_event_status(sos_event_id, "no_contacts")
            return {
                "overall_status": "no_contacts",
                "total_contacts": 0,
                "dispatches": [],
                "summary": {
                    "sms_sent": 0,
                    "sms_simulated": 0,
                    "sms_failed": 0,
                    "telegram_sent": 0,
                    "telegram_simulated": 0,
                    "telegram_failed": 0
                }
            }

        sms_body = format_emergency_sms(
            user_name,
            trigger_type,
            maps_url=maps_url,
            latitude=latitude,
            longitude=longitude
        )
        telegram_body = TelegramProvider.format_emergency_message(
            user_name,
            trigger_type,
            latitude,
            longitude,
            maps_url
        )

        dispatches = []
        metrics = {
            "sms_sent": 0,
            "sms_simulated": 0,
            "sms_failed": 0,
            "telegram_sent": 0,
            "telegram_simulated": 0,
            "telegram_failed": 0
        }

        for contact in contacts:
            contact_id = contact.get("id")
            contact_name = contact.get("name", "Unknown Contact")
            phone = contact.get("phone")
            telegram_chat_id = contact.get("telegram_chat_id")

            contact_dispatch = {
                "contact_id": contact_id,
                "name": contact_name,
                "phone": phone,
                "telegram_chat_id": telegram_chat_id,
                "channels": {}
            }

            # ----------------------------------------------------
            # 1. SMS CHANNEL
            # ----------------------------------------------------
            if phone:
                try:
                    sms_result = self.sms.send_sms(phone, sms_body)
                    sms_status = sms_result.get("status", "sent" if sms_result.get("success") else "failed")
                    sms_provider_name = sms_result.get("provider", "mock")
                    error_msg = sms_result.get("error")

                    if sms_status == "sent":
                        metrics["sms_sent"] += 1
                    elif sms_status == "simulated":
                        metrics["sms_simulated"] += 1
                    else:
                        metrics["sms_failed"] += 1

                    contact_dispatch["channels"]["sms"] = {
                        "status": sms_status,
                        "provider": sms_provider_name,
                        "error": error_msg
                    }

                    if sos_event_id:
                        log_notification(
                            sos_event_id=sos_event_id,
                            contact_id=contact_id,
                            channel="sms",
                            recipient=phone,
                            status=sms_status,
                            provider=sms_provider_name,
                            error_message=error_msg
                        )

                except Exception as ex:
                    print(f"⚠️ NotificationService SMS exception for contact #{contact_id}: {ex}")
                    metrics["sms_failed"] += 1
                    contact_dispatch["channels"]["sms"] = {
                        "status": "failed",
                        "provider": "unknown",
                        "error": str(ex)
                    }
                    if sos_event_id:
                        log_notification(
                            sos_event_id=sos_event_id,
                            contact_id=contact_id,
                            channel="sms",
                            recipient=phone,
                            status="failed",
                            provider="unknown",
                            error_message=str(ex)
                        )

            # ----------------------------------------------------
            # 2. TELEGRAM CHANNEL
            # ----------------------------------------------------
            if telegram_chat_id:
                try:
                    tg_result = self.telegram.send_message(telegram_chat_id, telegram_body)
                    tg_status = tg_result.get("status", "sent" if tg_result.get("success") else "failed")
                    tg_provider_name = tg_result.get("provider", "telegram")
                    tg_error = tg_result.get("error")

                    if tg_status == "sent":
                        metrics["telegram_sent"] += 1
                    elif tg_status == "simulated":
                        metrics["telegram_simulated"] += 1
                    else:
                        metrics["telegram_failed"] += 1

                    contact_dispatch["channels"]["telegram"] = {
                        "status": tg_status,
                        "provider": tg_provider_name,
                        "error": tg_error
                    }

                    if sos_event_id:
                        log_notification(
                            sos_event_id=sos_event_id,
                            contact_id=contact_id,
                            channel="telegram",
                            recipient=telegram_chat_id,
                            status=tg_status,
                            provider=tg_provider_name,
                            error_message=tg_error
                        )

                except Exception as ex:
                    print(f"⚠️ NotificationService Telegram exception for contact #{contact_id}: {ex}")
                    metrics["telegram_failed"] += 1
                    contact_dispatch["channels"]["telegram"] = {
                        "status": "failed",
                        "provider": "telegram",
                        "error": str(ex)
                    }
                    if sos_event_id:
                        log_notification(
                            sos_event_id=sos_event_id,
                            contact_id=contact_id,
                            channel="telegram",
                            recipient=telegram_chat_id,
                            status="failed",
                            provider="telegram",
                            error_message=str(ex)
                        )

            dispatches.append(contact_dispatch)

        # ----------------------------------------------------
        # AGGREGATE OVERALL STATUS
        # ----------------------------------------------------
        total_sent = metrics["sms_sent"] + metrics["telegram_sent"]
        total_simulated = metrics["sms_simulated"] + metrics["telegram_simulated"]
        total_failed = metrics["sms_failed"] + metrics["telegram_failed"]

        if total_sent > 0:
            overall_status = "notification_sent"
        elif total_simulated > 0:
            overall_status = "simulated"
        elif total_failed > 0:
            overall_status = "delivery_failed"
        else:
            overall_status = "received"

        if sos_event_id:
            update_sos_event_status(sos_event_id, overall_status)

        return {
            "overall_status": overall_status,
            "total_contacts": len(contacts),
            "dispatches": dispatches,
            "summary": metrics
        }

    def send_test_notification(self, contact, user_name="You"):
        """
        Test notifications for an individual contact without triggering emergency sirens.
        Allows immediate verification of contact details (SMS and Telegram).
        """
        results = {}
        phone = contact.get("phone")
        telegram_chat_id = contact.get("telegram_chat_id")

        if phone:
            test_sms = format_test_sms(user_name)
            results["sms"] = self.sms.send_sms(phone, test_sms)

        if telegram_chat_id:
            test_tg = TelegramProvider.format_test_message(user_name)
            results["telegram"] = self.telegram.send_message(telegram_chat_id, test_tg)

        return results

    def send_sms(self, phone, message):
        """Backward-compatible helper method."""
        return self.sms.send_sms(phone, message)


notification_service = NotificationService()
