import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models.models import Emergency, SOSRequest, User, AlertNotification, AlertEvent
from backend.schemas.alerts import SOSRequestCreate, AlertNotificationCreate
from backend.schemas.enums import AlertMethod, SOSStatus, AlertStatus
from backend.utils.alerts import dispatch_alert
from backend.utils.sms import send_sms
from backend.crud.crud import create_emergency  


def create_sos_request(
    db: Session,
    user_id: int,
    alert_event: AlertEvent,
    device_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> SOSRequest:
    """
    Create a new SOSRequest row linked to an AlertEvent.
    Note: push/SMS dispatch is handled separately in send_sos_notifications().
    """
    sos = SOSRequest(
        user_id=user_id,
        alert_event_id=alert_event.id,
        device_id=device_id,
        status=SOSStatus.PENDING,
        latitude=latitude,
        longitude=longitude,
        dispatched=False,
        timestamp=datetime.now(timezone.utc)
    )

    db.add(sos)
    db.commit()
    db.refresh(sos)

    logging.info(f"🆘 SOS request created with ID {sos.id} for user {user_id}")
    return sos


def resolve_sos(db: Session, sos_id: int) -> Optional[SOSRequest]:
    """
    Mark an SOS as resolved.
    """
    sos = db.query(SOSRequest).filter(SOSRequest.id == sos_id).first()
    if not sos:
        return None

    sos.status = SOSStatus.RESOLVED
    db.commit()
    db.refresh(sos)
    return sos


def send_sos_notifications(db: Session, sos: SOSRequest) -> List[AlertNotification]:
    """
    Send SOS notifications to all emergency contacts.
    Persists AlertNotification in DB, sends push, SMS, and creates an Emergency entry.
    ✅ Now includes user name and location URL in messages.
    """
    user: User = db.query(User).filter(User.id == sos.user_id).first()
    if not user:
        return []

    if not getattr(user, "emergency_contacts", None):
        return []

    notifications: List[AlertNotification] = []
    
    # ✅ Get user name
    user_name = getattr(user, "name", "Unknown User")

    for contact in user.emergency_contacts:
        # ✅ Build message with user name
        message = f"🚨 SOS Alert from {user_name}!\n"
        message += f"Emergency triggered at {sos.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        # ✅ Add location URL if available
        if sos.latitude and sos.longitude:
            message += f"\n📍 Location: https://maps.google.com/?q={sos.latitude},{sos.longitude}"

        # Persist AlertNotification
        notif_schema = AlertNotificationCreate(
            alert_event_id=sos.alert_event_id,
            method=AlertMethod.SMS.value if isinstance(AlertMethod.SMS, AlertMethod) else "SMS",
            recipient=contact.phone_number,
            message=message,
            status=AlertStatus.PENDING
        )

        try:
            db_notif = AlertNotification(**notif_schema.model_dump())
            db.add(db_notif)
            db.commit()
            db.refresh(db_notif)
            notifications.append(db_notif)
        except Exception as e:
            db.rollback()
            logging.warning(f"Failed to persist alert notification for contact {contact.phone_number}: {e}")
            continue

        # Attempt to send SMS (only send once!)
        try:
            send_sms(message, to_number=contact.phone_number)
            db_notif.status = AlertStatus.SENT
            db.commit()
            logging.info(f"✅ SOS SMS sent to {contact.phone_number}")
        except TypeError:
            # Fallback for older send_sms signature
            try:
                send_sms(message)
                db_notif.status = AlertStatus.SENT
                db.commit()
            except Exception as e:
                db_notif.status = AlertStatus.FAILED
                db.commit()
                logging.warning(f"Failed to send SMS for SOS notification to {contact.phone_number}: {e}")
        except Exception as e:
            db_notif.status = AlertStatus.FAILED
            db.commit()
            logging.warning(f"Failed to send SMS for SOS notification to {contact.phone_number}: {e}")

        # ✅ DON'T call dispatch_alert here - we already sent SMS above
        # If we called dispatch_alert(db_notif), it would send SMS AGAIN to the default test number
        # causing duplicate messages to +27838555008

    # Create an Emergency record representing the SOS
    try:
        emergency_payload = {
            "user_id": sos.user_id,
            "device_id": sos.device_id,
            "emergency_type": "sos_manual",
            "severity": "HIGH",
            "description": f"SOS triggered by {user_name} (user {user.id}) via device {sos.device_id}",
            "alert_event_id": sos.alert_event_id
        }
        
        if "create_emergency" in globals():
            create_emergency(db, emergency_payload)
        else:
            em = Emergency(**emergency_payload)
            db.add(em)
            db.commit()
            db.refresh(em)
        logging.info(f"🆘 Emergency record created for SOS {sos.id}")
    except Exception as e:
        logging.warning(f"Failed to create Emergency for SOS {sos.id}: {e}")

    return notifications
