# utils/threshold.py
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session

from backend.models.models import ThresholdProfile, ThresholdDefault
from backend.schemas.alerts import AlertEventCreate, ThresholdCheckResult, ThresholdCheckResponse
from backend.schemas.enums import ThresholdSeverity
import logging

logger = logging.getLogger(__name__)


def _get_min_max_from_obj(obj) -> tuple[Optional[float], Optional[float]]:
    """
    Read min/max values from an object that might use either
    ('low', 'high') or ('min_value', 'max_value').
    """
    if obj is None:
        return None, None

    low = None
    high = None

    # prefer 'low' / 'high' where present
    if hasattr(obj, "low"):
        try:
            low = getattr(obj, "low")
        except Exception:
            low = None
    if hasattr(obj, "high"):
        try:
            high = getattr(obj, "high")
        except Exception:
            high = None

    # fallback to min_value / max_value
    if low is None and hasattr(obj, "min_value"):
        try:
            low = getattr(obj, "min_value")
        except Exception:
            low = None
    if high is None and hasattr(obj, "max_value"):
        try:
            high = getattr(obj, "max_value")
        except Exception:
            high = None

    return low, high


def evaluate_threshold(
    db: Session,
    user_id: int,
    vital_type: str,
    value: float
) -> Optional[AlertEventCreate]:
    """
    Evaluate a single vital against user-specific thresholds or system defaults.
    """
    try:
        # 1) Try user-specific profile
        profile = db.query(ThresholdProfile).filter_by(user_id=user_id, vital_type=vital_type).first()

        if profile:
            min_val, max_val = _get_min_max_from_obj(profile)
        else:
            # 2) Fallback to system default
            default = db.query(ThresholdDefault).filter_by(vital_type=vital_type).first()
            if not default:
                return None
            min_val, max_val = _get_min_max_from_obj(default)

        # If both min and max are None, nothing to check
        if min_val is None and max_val is None:
            return None

        # 3) Determine breach severity
        severity: Optional[ThresholdSeverity] = None
        try:
            numeric_value = float(value)
        except Exception:
            numeric_value = value

        if (min_val is not None) and (numeric_value < min_val):
            severity = ThresholdSeverity.LOW
        elif (max_val is not None) and (numeric_value > max_val):
            severity = ThresholdSeverity.HIGH

        if severity:
            return AlertEventCreate(
                user_id=user_id,
                health_data_id=0,  # caller should set real health_data id
                vital_type=vital_type,
                value=numeric_value,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
                resolved=False
            )

        return None

    except Exception as e:
        logger.exception(
            "evaluate_threshold error for user=%s vital=%s value=%s: %s",
            user_id, vital_type, value, e
        )
        return None


def check_thresholds(
    db: Session,
    user_id: int,
    health_data_obj
) -> List[Tuple[str, float, ThresholdSeverity]]:
    """
    Evaluate all relevant vitals in a HealthData object.
    """
    alerts: List[Tuple[str, float, ThresholdSeverity]] = []

    vital_attrs = [
        'heart_rate',
        'blood_pressure_systolic',
        'blood_pressure_diastolic',
        'temperature',
        'oxygen_saturation',
        'respiratory_rate'
    ]

    for vital in vital_attrs:
        try:
            value = getattr(health_data_obj, vital, None)
            if value is None:
                continue
            alert = evaluate_threshold(db, user_id, vital, value)
            if alert:
                alerts.append((vital, value, alert.severity))
        except Exception as e:
            logger.warning("check_thresholds: skipped %s due to error: %s", vital, e)

    return alerts


def simulate_thresholds(
    db: Session,
    user_id: int,
    vitals: Dict[str, float]
) -> ThresholdCheckResponse:
    """
    Simulate threshold evaluation without creating AlertEvents in the DB.
    """
    results: List[ThresholdCheckResult] = []

    for vital, value in vitals.items():
        alert = evaluate_threshold(db, user_id, vital, value)
        if alert:
            results.append(
                ThresholdCheckResult(
                    vital_type=vital,
                    value=float(value),
                    severity=alert.severity
                )
            )

    return ThresholdCheckResponse(
        user_id=user_id,
        health_data_id=0,  # simulation → no actual health_data row
        alerts=results
    )

