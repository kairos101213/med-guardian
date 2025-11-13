import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from backend.database.database import get_db
from backend.schemas.health_data import HealthDataCreate, HealthDataResponse, HealthDataUpdate
from backend.schemas.alerts import AlertEventCreate
from backend import crud as crud_health
from backend.crud.crud import create_alert_event
from backend.models.models import User
from backend.utils.security import get_current_user
from backend.schemas.enums import UserRole
from backend.utils.threshold import check_thresholds

router = APIRouter(
    prefix="/health-data",
    tags=["Health Data"],
    dependencies=[Depends(get_current_user)]
)

# ---------------- CREATE HEALTH DATA ----------------
@router.post("/", response_model=HealthDataResponse)
def create_health_data(
    data: HealthDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new health data record for the logged-in user.
    Triggers threshold evaluation and sends alerts (SMS + push) including user name and location.
    """
    try:
        # --- Step 1: Save health data ---
        stored_data = crud_health.create_health_data(
            db=db,
            data=data,
            user_id=current_user.id,
            current_user=current_user  # pass current_user so CRUD can include user name in alerts
        )
        logging.info(f"✅ Health data stored: {stored_data.id}")

        # --- Step 2: Optional additional threshold check (if using check_thresholds for legacy alerts) ---
        alerts = check_thresholds(db, current_user.id, data)
        if alerts:
            for alert_info in alerts:
                vital, value, severity = alert_info
                alert_event = AlertEventCreate(
                    user_id=current_user.id,
                    health_data_id=stored_data.id,
                    vital_type=vital,
                    value=value,
                    severity=severity,
                    timestamp=datetime.now(timezone.utc),
                    resolved=False
                )
                create_alert_event(db, alert_event)
                logging.info(f"⚠️ Alert created for {vital} = {value} (Severity: {severity})")

        return stored_data

    except HTTPException as he:
        logging.warning(f"HTTP error: {he.detail}")
        raise he
    except Exception as e:
        logging.error(f"Unexpected error creating health data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------- GET ALL HEALTH DATA ----------------
@router.get("/", response_model=List[HealthDataResponse])
def get_all_health_data(
    user_id: Optional[int] = Query(None, description="Filter by user_id"),
    device_id: Optional[int] = Query(None, description="Filter by device_id"),
    from_ts: Optional[datetime] = Query(None, description="ISO datetime lower bound"),
    to_ts: Optional[datetime] = Query(None, description="ISO datetime upper bound"),
    limit: Optional[int] = Query(None, description="Limit number of rows returned"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve health data records with optional filters:
      - user_id (non-admins will be limited to their own id)
      - device_id
      - from_ts / to_ts (ISO datetimes)
      - limit
    """
    try:
        return crud_health.get_health_data_filtered(db, user_id=user_id, from_ts=from_ts, to_ts=to_ts, current_user=current_user, device_id=device_id, limit=limit)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error retrieving health data: {e}")


# ---------------- GET SINGLE HEALTH DATA ----------------
@router.get("/{data_id}", response_model=HealthDataResponse)
def get_health_data(
    data_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a single health data record by ID. Only owner or admin can access."""
    data = crud_health.get_health_data(db, data_id)
    if not data or (data.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Health data not found")
    return data


# ---------------- UPDATE HEALTH DATA ----------------
@router.put("/{data_id}", response_model=HealthDataResponse)
def update_health_data(
    data_id: int,
    updates: HealthDataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing health data record. Only owner or admin can update."""
    existing_data = crud_health.get_health_data(db, data_id)
    if not existing_data or (existing_data.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Health data not found")
    return crud_health.update_health_data(db, data_id, updates)


# ---------------- DELETE HEALTH DATA ----------------
@router.delete("/{data_id}")
def delete_health_data(
    data_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a health data record. Only owner or admin can delete."""
    existing_data = crud_health.get_health_data(db, data_id)
    if not existing_data or (existing_data.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Health data not found")

    crud_health.delete_health_data(db, data_id)
    logging.info(f"🗑 Health data {data_id} deleted by user {current_user.id}")
    return {"detail": f"Health data with id {data_id} deleted"}
