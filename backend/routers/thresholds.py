from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.database.database import get_db
from backend.schemas.thresholds import (
    ThresholdDefaultCreate,
    ThresholdDefaultOut,
    ThresholdProfileCreate,
    ThresholdProfileOut,
    CustomThresholdsIn,
)
from backend.schemas.alerts import ThresholdCheckResponse
from backend.crud import crud
from backend.utils.security import get_current_user
from backend.schemas.enums import UserRole
from backend.models.models import ThresholdProfile, User
from backend.utils.threshold import simulate_thresholds

import logging

router = APIRouter(
    prefix="/thresholds",
    tags=["Thresholds"],
    dependencies=[Depends(get_current_user)],
)

logger = logging.getLogger(__name__)

# -------------------------------------------------
# ----- Threshold Defaults (Admin only) -----
# -------------------------------------------------
@router.post("/defaults", response_model=ThresholdDefaultOut)
def create_threshold_default(
    default: ThresholdDefaultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.create_threshold_default(db, default)


@router.get("/defaults", response_model=List[ThresholdDefaultOut])
def list_threshold_defaults(db: Session = Depends(get_db)):
    return crud.get_all_threshold_defaults(db)


# -------------------------------------------------
# ----- Threshold Profiles -----
# -------------------------------------------------
@router.post("/profiles", response_model=ThresholdProfileOut)
def create_threshold_profile(
    profile: ThresholdProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payload = profile.model_dump(exclude_unset=True)
    if current_user.role != UserRole.ADMIN:
        payload["user_id"] = current_user.id

    existing = (
        db.query(ThresholdProfile)
        .filter(
            ThresholdProfile.user_id == payload["user_id"],
            ThresholdProfile.vital_type == payload["vital_type"],
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Profile for this vital already exists")

    return crud.create_threshold_profile(db, ThresholdProfileCreate(**payload))


@router.get("/profiles", response_model=Dict[str, Any])
def get_user_profiles(
    user_id: int = Query(..., description="User ID to retrieve threshold profiles for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve merged threshold profiles for a user using query parameter (?user_id=).
    Combines custom and default thresholds for the specified user.
    """
    # Ensure users can only fetch their own profiles unless admin
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view these thresholds.")

    try:
        merged_profiles = crud.get_user_effective_thresholds(db, user_id)
    except Exception as e:
        logger.exception("Failed to fetch thresholds for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch threshold profiles")

    return merged_profiles


@router.get("/profiles/me", response_model=List[ThresholdProfileOut])
def get_my_threshold_profiles(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return crud.get_user_threshold_profiles(db, current_user.id)


# -------------------------------------------------
# ----- Customizable Thresholds -----
# -------------------------------------------------
@router.post("/custom", response_model=List[ThresholdProfileOut])
def create_or_update_custom_thresholds(
    body: CustomThresholdsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_user_id = (
        body.user_id if current_user.role == UserRole.ADMIN and body.user_id else current_user.id
    )
    return crud.create_or_update_user_custom_thresholds(db, target_user_id, body.thresholds)


@router.delete("/custom", response_model=List[ThresholdProfileOut])
def delete_custom_thresholds(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return crud.delete_user_custom_thresholds(db, current_user.id)


# -------------------------------------------------
# ----- Threshold Simulation -----
# -------------------------------------------------
@router.post("/simulate", response_model=ThresholdCheckResponse)
def simulate_threshold_endpoint(
    vitals: Dict[str, float],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return simulate_thresholds(db, current_user.id, vitals)
