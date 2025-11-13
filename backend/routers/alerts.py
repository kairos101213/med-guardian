from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from backend.database.database import get_db
from backend.schemas.alerts import (
    AlertEventCreate,
    AlertEventOut,
    AlertNotificationCreate,
    AlertNotificationOut
)
from backend.crud.crud import (
    create_alert_event,
    create_alert_notification,
    get_all_notifications,
    get_notification_by_id,
    delete_notification,
    get_notifications_for_user
)
from backend.utils.security import get_current_user, _role_to_str
from backend.utils.threshold import evaluate_threshold
from backend.utils.alerts import format_alert_message
from backend.models.models import User
from pydantic import BaseModel

router = APIRouter(
    prefix="/alerts",
    tags=["Alerts"]
)

class AlertEventRequest(BaseModel):
    user_id: int
    health_data_id: int
    vital_data: Dict[str, float]

# ---------------- ALERT EVENTS ----------------
@router.post("/events", response_model=List[AlertEventOut])
def trigger_alert_events(
    request: AlertEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert_events = []
    user_role = _role_to_str(current_user.role)

    if user_role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: users can only trigger alerts for themselves.")

    for vital, value in request.vital_data.items():
        alert_schema: AlertEventCreate = evaluate_threshold(db, request.user_id, vital, value)

        if alert_schema:
            # ✅ Inject user_name for message formatting
            alert_schema.user_name = getattr(current_user, "name", "Unknown User")
            alert_schema.health_data_id = request.health_data_id

            # ✅ Format message with user_name
            if not alert_schema.message:
                alert_schema.message = format_alert_message(alert_schema)

            # ✅ Create alert event (create_alert_event should handle removing user_name)
            created_alert = create_alert_event(db, alert_schema)
            alert_events.append(created_alert)

            # ✅ Create notification with formatted message
            notif_schema = AlertNotificationCreate(
                alert_event_id=created_alert.id,
                method="push",
                message=alert_schema.message,  # Already formatted with user_name
                recipient=None
            )

            devices = current_user.devices
            fcm_tokens = [d.fcm_token for d in devices if d.fcm_token]
            create_alert_notification(db, notif_schema, fcm_tokens=fcm_tokens)

    return alert_events


# ---------------- ALERT NOTIFICATIONS ----------------
@router.post("/notifications", response_model=AlertNotificationOut)
def create_alert_notification_endpoint(
    notification: AlertNotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    devices = current_user.devices
    fcm_tokens = [d.fcm_token for d in devices if d.fcm_token]

    if not fcm_tokens:
        raise HTTPException(status_code=400, detail="No registered FCM tokens for user devices")

    return create_alert_notification(db, notification, fcm_tokens=fcm_tokens)

@router.get("/notifications", response_model=List[AlertNotificationOut])
def list_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_notifications_for_user(db, current_user.id)


@router.get("/notifications/{notification_id}", response_model=AlertNotificationOut)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    note = get_notification_by_id(db, notification_id)
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")
    return note

@router.delete("/notifications/{notification_id}")
def delete_notification_endpoint(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = delete_notification(db, notification_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"detail": "Notification deleted successfully"}
