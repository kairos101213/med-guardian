import logging
from typing import Any, Dict
from backend.schemas.enums import (
    Gender,
    HealthContext,
    ThresholdCategory,
    UserRole,
    SOSStatus,
    ThresholdSeverity,
    AlertMethod,
    AlertStatus
)

# Mapping of keys in payload -> their Enum class
ENUM_MAP = {
    "gender": Gender,
    "health_context": HealthContext,
    "threshold_category": ThresholdCategory,
    "role": UserRole,
    "sos_status": SOSStatus,
    "severity": ThresholdSeverity,
    "alert_method": AlertMethod,
    "alert_status": AlertStatus,
}


def _normalize_single_enum(value: Any, enum_class) -> Any:
    """
    Robustly normalize a single value to the enum_class.value (lowercase string).
    Handles:
      - enum member instances (has .value)
      - strings that are enum values (case-insensitive)
      - strings that are enum NAMES (e.g. "MALE")
    Returns the enum.value (string) or None if can't normalize.
    """
    if value is None:
        return None

    # If it's already an Enum member instance, use its .value
    if hasattr(value, "value"):
        try:
            return enum_class(value.value).value if isinstance(value.value, str) else value.value
        except Exception:
            # If value.value isn't directly acceptable, attempt fallback to raw .value
            return str(value.value).lower()

    # If it's a string, try these in order:
    if isinstance(value, str):
        v = value.strip()
        # 1) try to interpret as enum value (case-insensitive)
        try:
            return enum_class(v.lower()).value
        except Exception:
            pass
        # 2) try to interpret as enum NAME (case-insensitive)
        try:
            # enum_class[NAME] expects exact name, so upper()
            return enum_class[v.upper()].value
        except Exception:
            pass

    # Unknown type / can't parse
    logging.warning(f"normalize_enum_values: could not normalize value '{value}' for enum {enum_class}")
    return None


def normalize_enum_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts values in payload to DB-safe enum string values.
    Ensures keys in ENUM_MAP are normalized to the enum.value (lowercase strings defined in schemas/enums).

    Example transformations:
      - {"gender": "male"} -> {"gender": "male"}
      - {"gender": "MALE"} -> {"gender": "male"}
      - {"gender": Gender.MALE} -> {"gender": "male"}
      - missing health_context -> set to HealthContext.DEFAULT.value
    """
    if not isinstance(payload, dict):
        # defensive: if profile passed as model instance, upstream should convert – but handle gracefully
        logging.warning("normalize_enum_values: payload is not a dict")
        return payload

    normalized = dict(payload)  # shallow copy

    for key, enum_class in ENUM_MAP.items():
        if key in normalized:
            normalized[key] = _normalize_single_enum(normalized.get(key), enum_class)

    # Ensure health_context default exists and is correct string value if absent or None
    if normalized.get("health_context") is None:
        normalized["health_context"] = HealthContext.DEFAULT.value

    # Remove threshold_category from payload if you don't intend to store it on UserProfile
    # (some code paths expect it for threshold provisioning but not for the DB user_profile).
    # Keep removal logic upstream (router) if desired; here we won't add it.
    # normalized.pop("threshold_category", None)

    return normalized

