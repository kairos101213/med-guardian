import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database.database import get_db
from backend.models.models import AlertEvent, User
from backend.schemas.alerts import AlertEventOut, SOSRequestCreate, AlertEventCreate
from backend.utils.security import get_current_user
from backend.utils.sos import create_sos_request, send_sos_notifications
from backend.crud.crud import create_alert_event, get_user, get_device
from backend.schemas.enums import UserRole

router = APIRouter(
    prefix="/sos",
    tags=["SOS"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# ---------------- TRIGGER SOS ----------------
@router.post("/", response_model=AlertEventOut, status_code=status.HTTP_201_CREATED)
def trigger_sos(
    sos_data: SOSRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Authorization
    if current_user.id != sos_data.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate user
    user = get_user(db, sos_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate device
    device = None
    if sos_data.device_id:
        device = get_device(db, sos_data.device_id)
        if not device or device.user_id != sos_data.user_id:
            raise HTTPException(status_code=404, detail="Device not found or does not belong to user")

    # ✅ Use AlertEventCreate (schema), not raw ORM
    alert_event_schema = AlertEventCreate(
        user_id=sos_data.user_id,
        health_data_id=None,
        vital_type="sos",
        value=0.0,
        severity=sos_data.severity,
        message="SOS alert triggered",
        latitude=sos_data.latitude,
        longitude=sos_data.longitude,
        vitals_snapshot=sos_data.vitals_snapshot,
        resolved=False
    )
    alert_event = create_alert_event(db, alert_event_schema)

    # Create SOSRequest (now links to the generated alert_event)
    sos_request = create_sos_request(
        db=db,
        user_id=sos_data.user_id,
        alert_event=alert_event,
        device_id=device.id if device else None,
        latitude=sos_data.latitude,
        longitude=sos_data.longitude
    )

    # Send notifications (placeholder, will wire real later)
    try:
        send_sos_notifications(db, sos_request)
    except Exception as e:
        logger.warning("Failed to send SOS notifications: %s", e)

    return AlertEventOut.model_validate(alert_event, from_attributes=True)


# ---------------- GET USER SOS ----------------
@router.get("/user/{user_id}", response_model=List[AlertEventOut])
def get_user_sos_alerts(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sos_alerts = db.query(AlertEvent).filter(
        AlertEvent.user_id == user_id,
        AlertEvent.vital_type == "sos"
    ).all()

    return [AlertEventOut.model_validate(alert, from_attributes=True) for alert in sos_alerts]



