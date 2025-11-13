import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# ---------------- FIREBASE INITIALIZATION ----------------
if not firebase_admin._apps:
    firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

    if firebase_creds_json:
        try:
            # Parse the JSON string safely
            creds_dict = json.loads(firebase_creds_json)

            # Fix for Render / escaped newlines in private_key
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully")

        except Exception as e:
            logger.error(f"⚠️ Failed to initialize Firebase: {e}")
    else:
        logger.warning("⚠️ No FIREBASE_CREDENTIALS_JSON env var set — push notifications disabled.")


# ---------------- PUSH SENDER ----------------
def send_push_notification(tokens, title: str, body: str, data: dict = None):
    """
    Send push notification via FCM.
    tokens can be a single string or list of strings.
    """
    if not tokens:
        logger.warning("⚠️ No FCM tokens provided")
        return

    if isinstance(tokens, str):
        tokens = [tokens]

    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
            data=data or {}
        )
        response = messaging.send_multicast(message)
        logger.info(
            f"📲 Push sent. Success: {response.success_count}, Failures: {response.failure_count}"
        )
    except Exception as e:
        logger.error("Push notification failed: %s", e)
