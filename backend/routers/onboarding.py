from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.crud.crud import (
    create_user_profile,
    provision_threshold_profiles_from_json,
    THRESHOLDS_JSON,
    get_user_profile,
    refresh_user_default_thresholds
)
from backend.database.database import get_db
from backend.schemas.onboarding import OnboardingRequest, OnboardingResponse
from backend.schemas.enums import ThresholdCategory
from backend.schemas.user import UserProfileCreate, UserProfileOut
from backend.utils.security import get_current_user
from backend.utils.normalisation import normalize_enum_values
from backend.models.models import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

def determine_category(profile: OnboardingRequest) -> str:
    """
    Determines the user's threshold category based on age, activity level, and chronic condition.
    """
    age = profile.age
    chronic = bool(profile.chronic_condition)
    activity = (profile.activity_level or "").lower()

    # Elderly
    if age >= 60 and not chronic and activity != "athlete":
        if 60 <= age < 70:
            return ThresholdCategory.elderly_60s.value
        elif 70 <= age < 80:
            return ThresholdCategory.elderly_70s.value
        else:
            return ThresholdCategory.elderly_80s.value

    # Athletes
    if activity == "athlete":
        if age < 30:
            return ThresholdCategory.athlete_young.value
        elif 30 <= age < 60:
            return ThresholdCategory.athlete_adult.value
        else:
            return ThresholdCategory.athlete_senior.value

    # Chronic
    if chronic:
        if age < 30:
            return ThresholdCategory.chronic_young.value
        elif 30 <= age < 60:
            return ThresholdCategory.chronic_adult.value
        else:
            return ThresholdCategory.chronic_senior.value

    return ThresholdCategory.DEFAULT.value


def _extract_low_high(obj):
    """Ensure a threshold entry has 'low' and 'high'."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        low = obj.get("low")
        high = obj.get("high")
        if low is None and high is None:
            return None
        return {"low": low, "high": high}
    try:
        v = float(obj)
        return {"low": v, "high": v}
    except Exception:
        return None


def _normalize_thresholds_json(raw: dict) -> dict:
    """
    Flatten thresholds JSON to {vital_type: {low, high}}.
    Handles blood_pressure separately.
    """
    thresholds = {}
    if not raw or not isinstance(raw, dict):
        return thresholds

    for vital in ["heart_rate", "oxygen_saturation", "temperature"]:
        if vital in raw:
            out = _extract_low_high(raw[vital])
            if out:
                thresholds[vital] = out

    bp = raw.get("blood_pressure")
    if isinstance(bp, dict):
        for bp_type in ["systolic", "diastolic"]:
            if bp_type in bp:
                out = _extract_low_high(bp[bp_type])
                if out:
                    thresholds[f"blood_pressure_{bp_type}"] = out

    return thresholds


# ----------------------------------------------------------------------
# POST /onboarding (existing)
# ----------------------------------------------------------------------
@router.post("/", response_model=OnboardingResponse)
def onboarding(
    profile: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Initial onboarding – creates a user profile and provisions default thresholds.
    """
    normalized_payload = normalize_enum_values(profile.model_dump())

    # Determine threshold category
    category_str = determine_category(profile)

    # Update/create user profile
    user_profile = create_user_profile(db, current_user.id, normalized_payload)

    # Select thresholds from JSON
    thresholds_key = category_str.lower()
    if thresholds_key not in THRESHOLDS_JSON:
        thresholds_key = "default"

    raw_thresholds = THRESHOLDS_JSON.get(thresholds_key, {})
    thresholds_json = _normalize_thresholds_json(raw_thresholds)
    logger.debug("Normalized thresholds: %s", thresholds_json)

    # Provision ThresholdProfile rows
    try:
        created_profiles = provision_threshold_profiles_from_json(
            db, current_user.id, thresholds_json, category_str
        )
    except Exception as e:
        logger.exception("Failed to provision threshold profiles: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to provision threshold profiles"
        )

    return OnboardingResponse(
        user_id=current_user.id,
        assigned_category=category_str,
        thresholds={p.vital_type: {"low": p.low, "high": p.high} for p in created_profiles},
        created_profiles_count=len(created_profiles),
    )


# ----------------------------------------------------------------------
# GET /onboarding
# ----------------------------------------------------------------------
@router.get("/", response_model=UserProfileOut)
def get_onboarding_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the stored onboarding (demographics) for the authenticated user.
    Used on the Profile page to display name, email, age, etc.
    """
    profile = get_user_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ----------------------------------------------------------------------
# PUT /onboarding
# ----------------------------------------------------------------------
@router.put("/", response_model=UserProfileOut)
def update_onboarding_profile(
    profile: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the user's onboarding/demographics information and refresh
    any thresholds that depend on demographic defaults.
    Custom thresholds remain unchanged.
    """
    normalized_payload = normalize_enum_values(profile.model_dump())

    # Update or create the UserProfile
    updated_profile = create_user_profile(db, current_user.id, normalized_payload)

    # Determine threshold category based on new demographics
    category_str = determine_category(profile)
    thresholds_key = category_str.lower()
    if thresholds_key not in THRESHOLDS_JSON:
        thresholds_key = "default"

    # Get new default thresholds
    raw_thresholds = THRESHOLDS_JSON.get(thresholds_key, {})
    normalized_thresholds = _normalize_thresholds_json(raw_thresholds)

    # Refresh only default-based thresholds in DB
    try:
        refresh_user_default_thresholds(
            db=db, user_id=current_user.id, normalized_thresholds=normalized_thresholds
        )
    except Exception as e:
        logger.exception("Failed to refresh user default thresholds: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to refresh default thresholds"
        )

    logger.info(
        f"User {current_user.id} updated demographics; defaults refreshed for category {category_str}"
    )

    return updated_profile
