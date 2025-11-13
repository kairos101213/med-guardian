import logging
from typing import Optional, Dict, Union, Any

from backend.schemas.alerts import AlertEventCreate, AlertNotificationCreate
from backend.schemas.enums import AlertMethod
from backend.utils.sms import send_sms
from backend.utils.firebase import send_push_notification

logger = logging.getLogger(__name__)

# ---------------- ALERT MESSAGE FORMATTING ----------------
def format_alert_message(alert: Union["AlertEventCreate", "AlertNotificationCreate", dict, Any]) -> str:
    """
    Returns a professional, human-readable alert message for SMS/notifications.
    
    Accepts:
    - dict payload (preferred)
    - AlertEventCreate / AlertNotificationCreate model
    - any object with compatible attributes
    
    Uses:
    - 'name' or 'user_name' for user name
    - 'vital_type', 'value', 'severity'
    - optional 'latitude' / 'longitude' for map link
    """
    try:
        # ✅ Normalize input type
        if isinstance(alert, dict):
            getter = alert.get
        else:
            getter = lambda key, default=None: getattr(alert, key, default)

        # ---------------- User ----------------
        user_name = getter("user_name") or getter("name") or "Unknown User"

        # ---------------- Vital info ----------------
        vital_type = getter("vital_type")
        value = getter("value")
        severity = getter("severity")

        # Handle Enum or string severity
        if hasattr(severity, "value"):
            severity_str = severity.value.upper()
        elif isinstance(severity, str):
            severity_str = severity.upper()
        else:
            severity_str = "UNKNOWN"

        # Round numeric values neatly
        if isinstance(value, float):
            value = round(value, 1)

        # ---------------- Location ----------------
        lat = getter("latitude")
        lng = getter("longitude")
        location_url = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None

        # ---------------- Compose message ----------------
        if vital_type:
            msg_lines = [
                f"🚨 ALERT for {user_name} 🚨",
                f"{vital_type.upper()} breached {severity_str} threshold.",
                f"Value: {value}"
            ]
            if location_url:
                msg_lines.append(f"📍 Last known location: {location_url}")
            return "\n".join(msg_lines)

        # ---------------- Fallback for notification messages ----------------
        alert_event_id = getter("alert_event_id")
        method = getter("method")
        if alert_event_id and method:
            method_str = getattr(method, "value", str(method)).upper()
            return f"ALERT NOTIFICATION: Event {alert_event_id} triggered via {method_str}."

    except Exception as e:
        logging.warning(f"⚠️ Failed to format alert message: {e}")

    # ---------------- Default fallback ----------------
    return "ALERT: Threshold breached."



# ---------------- ALERT DISPATCH ----------------
def dispatch_alert(alert_obj: Union[AlertEventCreate, AlertNotificationCreate, Any]):
    """
    Dispatches an alert via SMS or Push.
    - Called after creating AlertNotifications.
    - Does not raise exceptions (logs instead).
    
    ⚠️ NOTE: For SMS, this should ONLY be used for system alerts without a specific recipient.
    For emergency contact notifications, send SMS directly with to_number parameter.
    """
    try:
        message = getattr(alert_obj, "message", None) or format_alert_message(alert_obj)
        method = getattr(alert_obj, "method", None)

        if not method:
            logger.info("System alert (no method specified): %s", message)
            return

        method_val = getattr(method, "value", str(method)).lower()

        if method_val == AlertMethod.PUSH.value:
            recipient = getattr(alert_obj, "recipient", None)
            send_push_notification(tokens=recipient, title="⚠️ Alert", body=message)
            logger.info("✅ Push notification sent")
        elif method_val == AlertMethod.SMS.value:
            # ✅ Only send if there's a specific recipient
            # Otherwise it sends to the default test number (causing duplicates)
            recipient = getattr(alert_obj, "recipient", None)
            if recipient:
                try:
                    send_sms(message, to_number=recipient)
                    logger.info(f"✅ SMS sent to {recipient}")
                except Exception as e:
                    logger.error(f"SMS dispatch failed to {recipient}: %s", e)
            else:
                logger.info("⚠️ SMS notification has no recipient, skipping (would send to test number)")
        else:
            logger.info("System alert (method=%s): %s", method_val, message)

    except Exception as e:
        logger.error("dispatch_alert failed: %s", e)
