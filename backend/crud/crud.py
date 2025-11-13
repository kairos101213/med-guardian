import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta, timezone
import secrets
import random
from typing import Dict, Optional, List, Union, Any, Type

from backend.models.models import (
    EmailOTP, User, Device, HealthData, EmergencyContact, Emergency,
    ThresholdDefault, ThresholdProfile, AlertEvent, AlertNotification,
    RefreshToken, UserProfile
)
from backend.schemas.thresholds import (
    ThresholdProfileOut, ThresholdValueIn,
    ThresholdProfileCreate, ThresholdDefaultCreate
)

from backend.schemas.user import UserCreate, UserUpdate, UserProfileCreate
from backend.schemas.device import DeviceCreate, DeviceUpdate
from backend.schemas.health_data import HealthDataCreate, HealthDataUpdate
from backend.schemas.emergency_contacts import (
    EmergencyContactCreate, EmergencyContactUpdate,
    EmergencyCreate, EmergencyUpdate
)

from backend.schemas.alerts import (
    SOSRequestCreate, AlertEventCreate, AlertNotificationCreate
)

from backend.schemas.auth import RegisterRequest
from backend.schemas.enums import (
    Gender, HealthContext, ThresholdCategory, UserRole,
    ThresholdSeverity, AlertMethod, AlertStatus, SOSStatus
)
from backend.utils.email import send_verification_email
from backend.utils.security import get_password_hash, verify_password
from backend.utils.sms import send_sms
from backend.utils.threshold import evaluate_threshold
from backend.utils.alerts import format_alert_message, dispatch_alert
from backend.utils.firebase import send_push_notification
from backend.utils.normalisation import normalize_enum_values


# Path to threshold defaults
THRESHOLDS_JSON_PATH = Path(__file__).parent.parent / "threshold_defaults.json"

# Load JSON once
try:
    with open(THRESHOLDS_JSON_PATH, "r") as f:
        THRESHOLDS_JSON = json.load(f)
except Exception as e:
    logging.exception("Failed to load threshold defaults JSON: %s", e)
    THRESHOLDS_JSON = {}

logger = logging.getLogger(__name__)

# ----------------------------
# Helpers
# ----------------------------

# Configuration (env-driven)
OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))
OTP_TTL_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "30"))
OTP_HASH_SECRET = os.getenv("OTP_HASH_SECRET", os.getenv("APP_SECRET", "change-this-secret"))

def _generate_numeric_otp(length: int = OTP_LENGTH) -> str:
    """Generate a secure numeric OTP as a zero-padded string."""
    if length <= 0:
        length = 6
    # secure random: use secrets
    import secrets
    max_val = 10 ** length - 1
    code = str(secrets.randbelow(max_val + 1)).zfill(length)
    return code

def _hash_otp(code: str) -> str:
    """HMAC-SHA256 hash of the OTP using secret. Returns hex digest."""
    key = OTP_HASH_SECRET.encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), hashlib.sha256).hexdigest()

def create_email_otp(db: Session, user_id: int, purpose: str = "email_verification", sent_via: str = "sendgrid", ip_address: str = None, user_agent: str = None) -> EmailOTP:
    """
    Create an EmailOTP record and return the created ORM object.
    Note: This function will generate a new OTP code, hash it, store the hash, and return the OTP in memory.
    For security you will receive the raw code only before returning (so caller can email it). The DB stores only hash.
    """
    # check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Generate code and hash
    code = _generate_numeric_otp()
    otp_hash = _hash_otp(code)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    otp = EmailOTP(
        user_id=user_id,
        otp_hash=otp_hash,
        created_at=now,
        expires_at=expires_at,
        used=False,
        attempts=0,
        purpose=purpose,
        sent_via=sent_via,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # return both otp record and the plaintext code to caller (caller must send and not log in prod)
    return otp, code

def invalidate_previous_otps(db: Session, user_id: int, purpose: str = "email_verification"):
    """Mark previous non-used OTPs as used=True (or expired) to avoid reuse."""
    now = datetime.now(timezone.utc)
    rows = db.query(EmailOTP).filter(
        EmailOTP.user_id == user_id,
        EmailOTP.purpose == purpose,
        EmailOTP.used == False
    ).all()
    for r in rows:
        r.used = True
        r.expires_at = now
    db.commit()

def get_latest_valid_otp(db: Session, user_id: int, purpose: str = "email_verification") -> EmailOTP:
    """Return the latest OTP object for the user/purpose that is not used and not expired, or None."""
    now = datetime.now(timezone.utc)
    otp = (
        db.query(EmailOTP)
        .filter(EmailOTP.user_id == user_id, EmailOTP.purpose == purpose, EmailOTP.used == False, EmailOTP.expires_at > now)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    return otp

def can_resend_otp(db: Session, user_id: int, purpose: str = "email_verification") -> bool:
    """Check last OTP create time to enforce resend cooldown."""
    last = (
        db.query(EmailOTP)
        .filter(EmailOTP.user_id == user_id, EmailOTP.purpose == purpose)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if not last:
        return True
    now = datetime.now(timezone.utc)
    diff = (now - last.created_at).total_seconds()
    return diff >= OTP_RESEND_COOLDOWN_SECONDS

def generate_and_send_email_otp(
    db: Session,
    user_id: int,
    to_email: str = None,
    ip_address: str = None,
    user_agent: str = None,
    invalidate_previous: bool = True,  # new param
) -> dict:
    """
    High-level: optionally invalidates previous OTPs, creates a new OTP, sends it via SendGrid.
    """
    if invalidate_previous:
        invalidate_previous_otps(db, user_id)

    otp_record, code = create_email_otp(db, user_id, ip_address=ip_address, user_agent=user_agent)

    if not to_email:
        user = db.query(User).filter(User.id == user_id).first()
        to_email = getattr(user, "email", None)

    sent = False
    send_error = None
    try:
        sent = bool(send_verification_email(to_email, code, expires_minutes=OTP_TTL_MINUTES))
        if sent:
            logger.info("Verification email sent for user_id=%s otp_id=%s to=%s", user_id, otp_record.id, to_email)
    except Exception as e:
        send_error = str(e)
        logger.exception("Failed to send verification email (user_id=%s to=%s): %s", user_id, to_email, e)
        sent = False

    response = {
        "ok": True,
        "sent": sent,
        "otp_id": otp_record.id,
        "otp_expires_at": otp_record.expires_at,
    }
    if not sent:
        response["send_error"] = send_error or "send_failed"
    return response


def verify_email_otp(db: Session, user_id: int, code: str, purpose: str = "email_verification") -> dict:
    """
    Validate provided code for the user.
    Returns dict: {"ok": True/False, "reason": "...", "user_verified": bool}
    """
    otp = get_latest_valid_otp(db, user_id, purpose)
    if not otp:
        return {"ok": False, "reason": "no_valid_code"}

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp.used = True
        db.commit()
        return {"ok": False, "reason": "max_attempts_exceeded"}

    # compare hashed codes
    provided_hash = _hash_otp(code)
    if not hmac.compare_digest(provided_hash, otp.otp_hash):
        # increment attempts
        otp.attempts = (otp.attempts or 0) + 1
        db.commit()
        remaining = max(0, OTP_MAX_ATTEMPTS - otp.attempts)
        return {"ok": False, "reason": "invalid_code", "attempts_left": remaining}

    # matched, mark used and set user verified
    otp.used = True
    db.commit()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"ok": False, "reason": "user_missing"}

    user.email_verified = True
    db.commit()
    db.refresh(user)

    return {"ok": True, "reason": "verified", "user_verified": True}

# ---------------------------- AUTH / OTP ----------------------------
def resend_email_otp(db: Session, email: str, ip_address: str = None, user_agent: str = None) -> dict:
    """
    Resend email OTP for the given email.
    Ensures cooldown is respected, generates a new OTP and invalidates previous ones
    so that only the latest OTP is valid.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal that email doesn't exist
        return {"message": "Verification code resent if account exists.", "otp_sent": False}

    if not can_resend_otp(db, user.id):
        return {"message": "Please wait before requesting another OTP.", "otp_sent": False}

    try:
        # Important change: invalidate_previous=True ensures only the newly sent OTP is valid
        response = generate_and_send_email_otp(
            db,
            user.id,
            to_email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            invalidate_previous=True  # updated from False to True
        )
        otp_sent = response.get("sent", False)
        return {"message": "Verification code resent if account exists.", "otp_sent": otp_sent}
    except Exception as e:
        logging.exception(f"Failed to resend OTP for {email}: {e}")
        return {"message": "Failed to resend OTP.", "otp_sent": False}


# ---------- UserProfile helpers (new) ----------
def get_user_profile(db: Session, user_id: int) -> Optional[UserProfile]:
    """
    Return the UserProfile row for a given user_id or None.
    """
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def refresh_user_default_thresholds(db: Session, user_id: int, normalized_thresholds: Dict[str, Dict[str, float]]) -> None:
    """
    Update the user's threshold profiles to match normalized defaults.

    - normalized_thresholds: mapping like {'heart_rate': {'low': 40.0, 'high': 120.0}, 'blood_pressure_systolic': {...}, ...}
    - For any existing ThresholdProfile for the user:
        - If category == ThresholdCategory.CUSTOMIZABLE -> SKIP (preserve user's custom threshold)
        - Otherwise (DEFAULT, BLOOD_PRESSURE etc) -> overwrite low/high with new defaults
    - If a default threshold is missing in DB -> create it (category: DEFAULT except blood_pressure parts get BLOOD_PRESSURE)
    """
    # load all existing profiles for this user to minimize queries
    existing_profiles = db.query(ThresholdProfile).filter(ThresholdProfile.user_id == user_id).all()
    existing_map = {p.vital_type: p for p in existing_profiles}

    # helper to choose a sensible category when creating new rows
    def _default_category_for_vital(vital_key: str):
        # blood pressure parts use BLOOD_PRESSURE enum constant (if defined)
        try:
            if vital_key.startswith("blood_pressure"):
                return ThresholdCategory.BLOOD_PRESSURE
        except Exception:
            pass
        # default to DEFAULT for the rest
        return ThresholdCategory.DEFAULT

    for vital_key, limit in normalized_thresholds.items():
        low = limit.get("low")
        high = limit.get("high")

        # if exists
        existing = existing_map.get(vital_key)
        if existing:
            # skip user-customized thresholds
            try:
                if existing.category == ThresholdCategory.CUSTOMIZABLE:
                    continue
            except Exception:
                # if category stored as string, try converting
                try:
                    if ThresholdCategory(existing.category) == ThresholdCategory.CUSTOMIZABLE:
                        continue
                except Exception:
                    pass

            # update the default profile values
            if low is not None:
                existing.low = low
            if high is not None:
                existing.high = high
            db.add(existing)

        else:
            # create missing default threshold profile
            category_enum = _default_category_for_vital(vital_key)
            new_profile = ThresholdProfile(
                user_id=user_id,
                vital_type=vital_key,
                low=low,
                high=high,
                category=category_enum,
                # default severity - pick LOW (or adjust if you need different default)
                severity=ThresholdSeverity.LOW
            )
            db.add(new_profile)

    db.commit()


def _to_enum(enum_class: Type, value: Any, fallback: Any = None):
    """
    Convert a value to an enum member if possible.
    Accepts:
      - enum member -> returns it
      - string equal to enum.value (case-insensitive)
      - string equal to enum name (case-insensitive)
    Returns fallback if conversion fails.
    """
    if value is None:
        return fallback

    # Already enum member
    if isinstance(value, enum_class):
        return value

    # If value has .value attribute (e.g. Pydantic enum)
    if hasattr(value, "value"):
        try:
            return enum_class(value.value)
        except Exception:
            try:
                return enum_class[value.value.upper()]
            except Exception:
                pass

    # If string, try by value then by name
    if isinstance(value, str):
        s = value.strip()
        # Try value (case-insensitive)
        for member in enum_class:
            if member.value.lower() == s.lower():
                return member
        # Try name (case-insensitive)
        try:
            return enum_class[s.upper()]
        except Exception:
            pass

    return fallback


def _make_threshold_profile_out_from_orm(obj, user_id_override=None):
    uid = user_id_override if user_id_override is not None else getattr(obj, "user_id", None)
    vital = getattr(obj, "vital_type")
    low = getattr(obj, "low", None)
    high = getattr(obj, "high", None)
    raw_cat = getattr(obj, "category", None)
    raw_sev = getattr(obj, "severity", None)
    category_enum = _to_enum(ThresholdCategory, raw_cat, ThresholdCategory.DEFAULT)
    severity_enum = _to_enum(ThresholdSeverity, raw_sev, ThresholdSeverity.LOW)
    return ThresholdProfileOut(
        id=getattr(obj, "id", 0) or 0,
        user_id=uid,
        vital_type=vital,
        low=low,
        high=high,
        category=category_enum,
        severity=severity_enum
    )


# ---------------------------- USERS ----------------------------
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user_with_password(db: Session, user: RegisterRequest) -> User:
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(name=user.name, email=user.email, hashed_password=hashed_password, role=UserRole.USER)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user(db: Session, user: UserCreate, password: Optional[str] = None, role: UserRole = UserRole.USER) -> User:
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="User with that email already exists")
    password_to_hash = password or secrets.token_urlsafe(10)
    hashed_password = get_password_hash(password_to_hash)
    db_user = User(name=user.name, email=user.email, hashed_password=hashed_password, role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_users(db: Session) -> List[User]:
    return db.query(User).all()


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, updates: UserUpdate):
    user = get_user(db, user_id)
    if user:
        for field, value in updates.model_dump(exclude_unset=True).items():
            if field == "password":
                user.hashed_password = get_password_hash(value)
            else:
                setattr(user, field, value)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db: Session, user_id: int):
    user = get_user(db, user_id)
    if not user:
        return None
    for data in list(user.health_data):
        delete_health_data(db, data.id)
    for alert in list(user.alert_events):
        db.delete(alert)
    for device in list(user.devices):
        for emergency in list(device.emergencies):
            db.delete(emergency)
        db.delete(device)
    for contact in list(user.emergency_contacts):
        db.delete(contact)
    for profile in list(user.threshold_profiles):
        db.delete(profile)
    for emergency in list(user.emergencies):
        db.delete(emergency)
    for rt in list(user.refresh_tokens):
        db.delete(rt)
    if user.profile:
        db.delete(user.profile)
    db.delete(user)
    db.commit()
    return user


# ---------------------------- USER PROFILE / ONBOARDING ----------------------------
def create_user_profile(db: Session, user_id: int, profile: dict):
    """
    Create or update a UserProfile for the given user_id.
    Ensures proper enum handling for health_context and gender.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    payload = profile
    if hasattr(profile, "model_dump"):
        payload = profile.model_dump()

    # Convert Pydantic enums to strings for DB
    for field in ["gender", "health_context"]:
        if field in payload and payload[field] is not None:
            val = payload[field]
            payload[field] = val.value if hasattr(val, "value") else val

    db_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if db_profile:
        for k, v in payload.items():
            setattr(db_profile, k, v)
    else:
        db_profile = UserProfile(user_id=user_id, **payload)
        db.add(db_profile)

    db.commit()
    db.refresh(db_profile)
    return db_profile


# ---------------------------- DEVICES ----------------------------
def create_device(db: Session, device: DeviceCreate):
    user = db.query(User).filter(User.id == device.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    db_device = Device(
        device_name=device.device_name,
        user_id=device.user_id,
        fcm_token=device.fcm_token  # ✅ now storing token
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_devices(db: Session, user_id: int = None) -> List[Device]:
    query = db.query(Device)
    if user_id:
        query = query.filter(Device.user_id == user_id)
    return query.all()


def get_device(db: Session, device_id: int) -> Optional[Device]:
    return db.query(Device).filter(Device.id == device_id).first()


def update_device(db: Session, device_id: int, updates: DeviceUpdate):
    device = get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    db.commit()
    db.refresh(device)
    return device


def delete_device(db: Session, device_id: int):
    device = get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # ✅ Step 1: Get all health_data IDs associated with this device
    health_data_ids = [hd.id for hd in device.health_data]
    
    # ✅ Step 2: Delete alert_events that reference the health_data (deepest dependency first)
    if health_data_ids:
        db.query(AlertEvent).filter(AlertEvent.health_data_id.in_(health_data_ids)).delete(synchronize_session=False)
    
    # ✅ Step 3: Delete alert_events that reference emergencies from this device
    emergency_ids = [em.id for em in device.emergencies]
    if emergency_ids:
        db.query(AlertEvent).filter(AlertEvent.id.in_(
            db.query(Emergency.alert_event_id).filter(Emergency.id.in_(emergency_ids))
        )).delete(synchronize_session=False)
    
    # ✅ Step 4: Delete emergencies
    for emergency in list(device.emergencies):
        db.delete(emergency)
    
    # ✅ Step 5: Delete health_data (now safe since alert_events are gone)
    db.query(HealthData).filter(HealthData.device_id == device_id).delete(synchronize_session=False)
    
    # ✅ Step 6: Finally delete the device itself
    db.delete(device)
    db.commit()
    
    return device


def create_health_data(db: Session, data: HealthDataCreate, user_id: int = None, current_user: User = None):
    """
    Creates HealthData (vitals only) and triggers threshold evaluation.
    Injects location info into AlertEvent if a threshold is breached.
    """
    try:
        device = db.query(Device).filter(Device.id == data.device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {data.device_id} not found")

        # Assign user_id if not provided explicitly
        if not user_id:
            user_id = device.user_id
        elif user_id != device.user_id:
            raise HTTPException(status_code=403, detail=f"Device {data.device_id} does not belong to user {user_id}")

        # Get user name for alert messages
        user_name = getattr(current_user, "name", None)
        if not user_name:
            user_obj = db.query(User).filter(User.id == user_id).first()
            user_name = getattr(user_obj, "name", "Unknown User")

        # Only save actual health metrics to HealthData
        vitals_payload = data.model_dump(exclude_unset=True)
        vitals_payload.pop("latitude", None)
        vitals_payload.pop("longitude", None)
        vitals_payload.pop("location_accuracy", None)
        vitals_payload["user_id"] = user_id
        if vitals_payload.get("timestamp") is None:
            vitals_payload.pop("timestamp", None)

        db_data = HealthData(**vitals_payload)
        db.add(db_data)
        db.commit()
        db.refresh(db_data)
        logging.info(f"✅ Health data created with ID {db_data.id} for user {user_id}")

        # Evaluate thresholds & create alerts
        vitals_list = [
            "heart_rate", "oxygen_saturation", "temperature",
            "respiratory_rate", "blood_pressure_systolic", "blood_pressure_diastolic"
        ]

        for vital in vitals_list:
            value = getattr(db_data, vital, None)
            if value is None:
                continue

            try:
                alert_schema = evaluate_threshold(db, user_id, vital, value)
                if not alert_schema:
                    continue

                # ✅ Inject user_name for message formatting ONLY
                alert_schema.user_name = user_name
                alert_schema.health_data_id = db_data.id
                
                # Format message with user_name included
                if not alert_schema.message:
                    alert_schema.message = format_alert_message(alert_schema)

                # Ensure severity enum is valid
                severity_val = alert_schema.severity
                if isinstance(severity_val, str):
                    try:
                        severity_enum = ThresholdSeverity[severity_val.upper()]
                    except Exception:
                        try:
                            severity_enum = ThresholdSeverity(severity_val)
                        except Exception:
                            severity_enum = ThresholdSeverity.LOW
                elif isinstance(severity_val, ThresholdSeverity):
                    severity_enum = severity_val
                else:
                    severity_enum = ThresholdSeverity.LOW

                # Prepare alert payload for DB (WITHOUT user_name)
                alert_payload = alert_schema.model_dump()
                alert_payload["severity"] = severity_enum
                alert_payload["latitude"] = data.latitude
                alert_payload["longitude"] = data.longitude

                # ✅ Remove fields that don't belong in AlertEvent model
                alert_payload.pop("location_accuracy", None)
                alert_payload.pop("user_name", None)  # Remove before DB insert

                db_alert = AlertEvent(**alert_payload)
                db.add(db_alert)
                db.commit()
                db.refresh(db_alert)
                logging.info(f"⚠️ Alert created for {vital} = {value} (Severity: {db_alert.severity}) with location")

                # --- Notifications ---
                contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()
                for contact in contacts:
                    try:
                        # Use pre-formatted message that already includes user_name
                        msg = db_alert.message
                        if db_alert.latitude and db_alert.longitude:
                            msg += f"\n📍 Last known location: https://maps.google.com/?q={db_alert.latitude},{db_alert.longitude}"

                        notif = AlertNotification(
                            alert_event_id=db_alert.id,
                            method=AlertMethod.SMS,
                            recipient=contact.phone_number,
                            message=msg,
                            status=AlertStatus.PENDING
                        )
                        db.add(notif)
                        db.commit()
                        db.refresh(notif)

                        try:
                            send_sms(msg, to_number=contact.phone_number)
                            notif.status = AlertStatus.SENT
                            db.commit()
                            db.refresh(notif)
                            logging.info(f"📩 SMS sent to {contact.phone_number} for alert_event {db_alert.id}")
                        except Exception as e:
                            notif.status = AlertStatus.FAILED
                            db.commit()
                            logging.warning(f"⚠️ Failed to send SMS to {contact.phone_number}: {e}")
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to create SMS notification for {contact.phone_number}: {e}")

                # Generic push notification
                try:
                    push_msg = db_alert.message
                    if db_alert.latitude and db_alert.longitude:
                        push_msg += f"\n📍 Last known location: https://maps.google.com/?q={db_alert.latitude},{db_alert.longitude}"
                    push_notif = AlertNotification(
                        alert_event_id=db_alert.id,
                        method=AlertMethod.PUSH,
                        recipient=None,
                        message=push_msg,
                        status=AlertStatus.PENDING
                    )
                    db.add(push_notif)
                    db.commit()
                    db.refresh(push_notif)
                    logging.info(f"📩 Push notification created for alert_event {db_alert.id}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to create push notification: {e}")

                # --- Emergency ---
                try:
                    emergency_payload = {
                        "user_id": user_id,
                        "device_id": db_data.device_id,
                        "emergency_type": f"threshold_breach:{vital}",
                        "severity": severity_enum.name if hasattr(severity_enum, "name") else str(severity_enum),
                        "description": f"Auto-created emergency for {vital} threshold breach (value: {value})",
                        "alert_event_id": db_alert.id
                    }
                    if "create_emergency" in globals():
                        create_emergency(db, emergency_payload)
                    else:
                        em = Emergency(**emergency_payload)
                        db.add(em)
                        db.commit()
                        db.refresh(em)
                    logging.info(f"🆘 Emergency created for alert_event {db_alert.id}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to create emergency for alert_event {db_alert.id}: {e}")

            except Exception as e:
                logging.warning(f"⚠️ Threshold evaluation skipped for {vital}: {e}")

        return db_data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error creating health data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def get_all_health_data(db: Session, user_id: int = None, device_id: int = None, from_ts: Optional[datetime] = None, to_ts: Optional[datetime] = None, limit: Optional[int] = None) -> List[HealthData]:
    """
    Generic getter used by the router. Accepts optional filters:
      - user_id
      - device_id
      - from_ts (datetime)
      - to_ts (datetime)
      - limit (int)
    """
    query = db.query(HealthData)

    if user_id:
        query = query.filter(HealthData.user_id == user_id)
    if device_id:
        query = query.filter(HealthData.device_id == device_id)
    if from_ts:
        query = query.filter(HealthData.timestamp >= from_ts)
    if to_ts:
        query = query.filter(HealthData.timestamp <= to_ts)
    # order by newest first
    query = query.order_by(HealthData.timestamp.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_health_data(db: Session, data_id: int) -> Optional[HealthData]:
    return db.query(HealthData).filter(HealthData.id == data_id).first()


def update_health_data(db: Session, data_id: int, updates: HealthDataUpdate) -> Optional[HealthData]:
    data = get_health_data(db, data_id)
    if data:
        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(data, field, value)
        db.commit()
        db.refresh(data)
    return data


def delete_health_data(db: Session, data_id: int) -> Optional[HealthData]:
    data = get_health_data(db, data_id)
    if not data:
        return None
    if data.alert_event:
        for note in list(data.alert_event.notifications):
            db.delete(note)
        db.delete(data.alert_event)
    db.delete(data)
    db.commit()
    return data


# ---------------- GET HEALTH DATA WITH FILTERS ----------------
def get_health_data_filtered(db: Session, user_id: Optional[int], from_ts: Optional[datetime], to_ts: Optional[datetime], current_user: Optional[User] = None, device_id: Optional[int] = None, limit: Optional[int] = None):
    """
    Backwards-compatible helper — intended to be called from router.
    Fix: compare current_user.role against UserRole.ADMIN (not ThresholdSeverity).
    """
    try:
        # if the caller is admin, return unfiltered set
        if current_user and current_user.role == UserRole.ADMIN:
            return get_all_health_data(db, user_id=user_id, device_id=device_id, from_ts=from_ts, to_ts=to_ts, limit=limit)

        # non-admins are restricted to their own data
        q_user_id = user_id if user_id and current_user and user_id == current_user.id else current_user.id if current_user else user_id
        return get_all_health_data(db, user_id=q_user_id, device_id=device_id, from_ts=from_ts, to_ts=to_ts, limit=limit)
    except Exception as e:
        logging.exception(f"Error retrieving health data: {e}")
        raise

# ---------------------------- EMERGENCY CONTACTS ----------------------------
def create_emergency_contact(db: Session, contact: EmergencyContactCreate, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    payload = contact.model_dump(exclude={"user_id"})
    db_contact = EmergencyContact(**payload, user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_all_emergency_contacts(db: Session, user_id: int) -> List[EmergencyContact]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return db.query(EmergencyContact).filter(EmergencyContact.user_id == user_id).all()


def get_emergency_contact(db: Session, contact_id: int, user_id: Optional[int] = None) -> EmergencyContact:
    query = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id)
    if user_id is not None:
        query = query.filter(EmergencyContact.user_id == user_id)
    contact = query.first()
    if not contact:
        raise HTTPException(status_code=404, detail=f"Emergency contact {contact_id} not found")
    return contact


def update_emergency_contact(db: Session, contact_id: int, user_id: int, updates: EmergencyContactUpdate):
    contact = get_emergency_contact(db, contact_id, user_id)
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_emergency_contact(db: Session, contact_id: int, user_id: int):
    contact = get_emergency_contact(db, contact_id, user_id)
    db.delete(contact)
    db.commit()
    return contact


# ---------------------------- EMERGENCIES ----------------------------
def create_emergency(db: Session, payload: dict) -> Emergency:
    """
    Create a new Emergency record with validation:
    - Normalize severity to ThresholdSeverity enum if a string is provided.
    - Ensure user exists and (if device_id provided) the device exists and belongs to user.
    - Provide clearer HTTP errors instead of raw 500s.
    """
    try:
        # Validate user exists
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        # If device supplied, validate it and ownership
        device_id = payload.get("device_id")
        if device_id is not None:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
            # If device exists but is owned by another user, reject
            if device.user_id != user_id:
                raise HTTPException(status_code=403, detail=f"Device {device_id} does not belong to user {user_id}")

        # Normalize severity to enum if necessary
        sev = payload.get("severity")
        if sev is None:
            raise HTTPException(status_code=400, detail="severity is required")
        # If it's a string, try to convert to ThresholdSeverity
        if isinstance(sev, str):
            try:
                # Try by name (e.g. "HIGH" -> ThresholdSeverity.HIGH)
                sev_enum = ThresholdSeverity[sev.upper()]
            except Exception:
                try:
                    # Try by value (e.g. "high")
                    sev_enum = ThresholdSeverity(sev)
                except Exception:
                    raise HTTPException(status_code=400, detail=f"Invalid severity value '{sev}'")
            payload["severity"] = sev_enum
        elif isinstance(sev, ThresholdSeverity):
            payload["severity"] = sev
        else:
            raise HTTPException(status_code=400, detail="Invalid severity type")

        # Ensure timestamp exists (model will default, but keep explicit)
        if "timestamp" not in payload or payload.get("timestamp") is None:
            payload["timestamp"] = datetime.now(timezone.utc)

        # Create emergency
        new_emergency = Emergency(**payload)
        db.add(new_emergency)
        db.commit()
        db.refresh(new_emergency)
        return new_emergency

    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"Failed to create emergency: {e}")
        raise HTTPException(status_code=500, detail="Failed to create emergency")


def get_emergency_by_id(db: Session, emergency_id: int) -> Optional[Emergency]:
    return db.query(Emergency).filter(Emergency.id == emergency_id).first()


def get_all_emergencies(db: Session) -> list[Emergency]:
    return db.query(Emergency).order_by(Emergency.timestamp.desc()).all()


def get_user_emergencies(db: Session, user_id: int) -> list[Emergency]:
    return db.query(Emergency).filter(Emergency.user_id == user_id).order_by(Emergency.timestamp.desc()).all()


def update_emergency(db: Session, emergency_id: int, update_data: EmergencyUpdate) -> Emergency:
    emergency = get_emergency_by_id(db, emergency_id)
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(emergency, field, value)
    db.commit()
    db.refresh(emergency)
    return emergency


def delete_emergency(db: Session, emergency_id: int):
    emergency = get_emergency_by_id(db, emergency_id)
    if not emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    db.delete(emergency)
    db.commit()


# ---------------------------- ALERTS ----------------------------
def create_alert_event(db: Session, alert_event: AlertEventCreate) -> AlertEvent:
    """
    Creates an AlertEvent in the database.
    Removes user_name before insertion since it's not a DB field.
    """
    try:
        # Convert to dict and remove non-DB fields
        data = alert_event.model_dump()
        data.pop("user_name", None)  # ✅ Remove user_name before DB insert
        data.pop("location_accuracy", None)  # Remove if present
        
        # Ensure severity is enum
        if isinstance(data.get("severity"), str):
            try:
                data["severity"] = ThresholdSeverity[data["severity"].upper()]
            except KeyError:
                data["severity"] = ThresholdSeverity.LOW
        
        db_alert = AlertEvent(**data)
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        logging.info(f"✅ AlertEvent {db_alert.id} created for user {db_alert.user_id}")
        return db_alert
        
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to create alert event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create alert event: {str(e)}")


def create_alert_notification(
    db: Session,
    notification: AlertNotificationCreate,
    fcm_tokens: List[str] = None
):
    """
    Create an AlertNotification in DB.
    Always send push (if FCM tokens), and also send SMS (currently your test number).
    """
    data = notification.model_dump()

    message = data.pop("message", f"Alert notification for event {data.get('alert_event_id')}.")
    method = data.get("method") or AlertMethod.PUSH

    db_notification = AlertNotification(
        **data,
        method=method,
        recipient=",".join(fcm_tokens) if fcm_tokens else None,
        message=message,
        status=AlertStatus.PENDING
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    # --- Push notification ---
    if fcm_tokens:
        try:
            for token in fcm_tokens:
                send_push_notification(token=token, title="⚠️ Alert", body=message)
            db_notification.status = AlertStatus.SENT
        except Exception as e:
            logging.warning(f"⚠️ Failed to send push notification: {e}")
            db_notification.status = AlertStatus.FAILED
        db.commit()
        db.refresh(db_notification)

    # --- SMS notification ---
    try:
        send_sms(message)  # routes to your test number
        logging.info("✅ SMS sent via SMS.to")
    except Exception as e:
        logging.warning(f"⚠️ Failed to send SMS: {e}")

    return db_notification


def get_alerts_for_user(db: Session, user_id: int) -> List[AlertEvent]:
    return db.query(AlertEvent).filter(AlertEvent.user_id == user_id).all()


def get_all_alerts(db: Session) -> List[AlertEvent]:
    return db.query(AlertEvent).all()


def get_alert_by_id(db: Session, alert_id: int) -> Optional[AlertEvent]:
    return db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()


def delete_alert(db: Session, alert_id: int):
    alert = get_alert_by_id(db, alert_id)
    if alert:
        for note in list(alert.notifications):
            db.delete(note)
        db.delete(alert)
        db.commit()
    return alert


def get_alert_notifications(db: Session, alert_event_id: int) -> List[AlertNotification]:
    return db.query(AlertNotification).filter(AlertNotification.alert_event_id == alert_event_id).all()


def get_all_notifications(db: Session) -> List[AlertNotification]:
    return db.query(AlertNotification).all()


def get_notification_by_id(db: Session, notification_id: int) -> Optional[AlertNotification]:
    return db.query(AlertNotification).filter(AlertNotification.id == notification_id).first()


def delete_notification(db: Session, notification_id: int):
    note = get_notification_by_id(db, notification_id)
    if note:
        db.delete(note)
        db.commit()
    return note

def get_notifications_for_user(db: Session, user_id: int) -> List[AlertNotification]:
    return (
        db.query(AlertNotification)
        .join(AlertEvent, AlertNotification.alert_event_id == AlertEvent.id)
        .filter(AlertEvent.user_id == user_id)
        .all()
    )


# ---------------------------- THRESHOLDS ----------------------------

# ----- Default Thresholds -----
def create_threshold_default(db: Session, threshold: ThresholdDefaultCreate) -> ThresholdDefault:
    db_threshold = ThresholdDefault(**threshold.model_dump())
    db.add(db_threshold)
    db.commit()
    db.refresh(db_threshold)
    return db_threshold


def get_all_threshold_defaults(db: Session) -> List[ThresholdDefault]:
    return db.query(ThresholdDefault).all()


# ----- User Threshold Profiles -----
def create_threshold_profile(db: Session, profile: ThresholdProfileCreate) -> ThresholdProfile:
    db_profile = ThresholdProfile(**profile.model_dump())
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def get_user_threshold_profiles(db: Session, user_id: int) -> List[ThresholdProfileOut]:
    """
    Return all threshold profiles for a user.
    Ensures that every default vital exists in the DB for this user.
    """
    defaults_json = THRESHOLDS_JSON.get("default", {})
    defaults: Dict[str, dict] = {}

    for vital, val in defaults_json.items():
        if vital == "blood_pressure":
            for bp_type, bp_val in val.items():
                defaults[f"blood_pressure_{bp_type}"] = bp_val
        else:
            defaults[vital] = val

    # Get all existing DB profiles for the user
    custom_list = db.query(ThresholdProfile).filter(ThresholdProfile.user_id == user_id).all()
    existing_vitals = {c.vital_type: c for c in custom_list}

    merged: List[ThresholdProfileOut] = []

    for vital, default_val in defaults.items():
        if vital in existing_vitals:
            # Already exists, return DB-backed profile
            merged.append(_make_threshold_profile_out_from_orm(existing_vitals[vital]))
        else:
            # Doesn't exist yet → create it in DB as onboarding default
            profile = ThresholdProfile(
                user_id=user_id,
                vital_type=vital,
                low=default_val.get("low"),
                high=default_val.get("high"),
                category=ThresholdCategory.DEFAULT,
                severity=ThresholdSeverity.LOW
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            merged.append(_make_threshold_profile_out_from_orm(profile))

    return merged


def get_threshold_for_vital(db, user_id, vital_type):
    profile = db.query(ThresholdProfile).filter(
        ThresholdProfile.user_id == user_id,
        ThresholdProfile.vital_type == vital_type
    ).first()
    if profile:
        return profile
    return db.query(ThresholdDefault).filter(ThresholdDefault.vital_type == vital_type).first()


def get_threshold_range(db, user_id, vital_type):
    threshold = get_threshold_for_vital(db, user_id, vital_type)
    if threshold:
        return {"low": threshold.low, "high": threshold.high}
    return None


# ----- Custom Threshold Management -----
def create_or_update_user_custom_thresholds(db, user_id, thresholds):
    results = []
    if not isinstance(thresholds, dict):
        raise HTTPException(status_code=400, detail="thresholds must be an object (vital -> {low, high})")

    for vital, val_obj in thresholds.items():
        if isinstance(val_obj, dict):
            val_obj = ThresholdValueIn(**val_obj)
        if not hasattr(val_obj, "low") or not hasattr(val_obj, "high"):
            raise HTTPException(status_code=400, detail=f"Invalid threshold payload for vital '{vital}'")
        if val_obj.low is None and val_obj.high is None:
            continue

        existing = db.query(ThresholdProfile).filter(
            ThresholdProfile.user_id == user_id,
            ThresholdProfile.vital_type == vital
        ).first()

        if existing:
            if val_obj.low is not None:
                existing.low = val_obj.low
            if val_obj.high is not None:
                existing.high = val_obj.high
            existing.category = ThresholdCategory.CUSTOMIZABLE  # store enum instance
            existing.severity = ThresholdSeverity.LOW  # enum instance
            db.commit()
            db.refresh(existing)
            results.append(_make_threshold_profile_out_from_orm(existing))
        else:
            new_profile = ThresholdProfile(
                user_id=user_id,
                vital_type=vital,
                low=val_obj.low,
                high=val_obj.high,
                category=ThresholdCategory.CUSTOMIZABLE,  # enum instance
                severity=ThresholdSeverity.LOW  # enum instance
            )
            db.add(new_profile)
            db.commit()
            db.refresh(new_profile)
            results.append(_make_threshold_profile_out_from_orm(new_profile))
    return get_user_threshold_profiles(db, user_id)


def delete_user_custom_thresholds(db, user_id):
    profiles_to_delete = db.query(ThresholdProfile).filter(
    ThresholdProfile.user_id == user_id,
    ThresholdProfile.category == ThresholdCategory.CUSTOMIZABLE
    ).all()
    for profile in profiles_to_delete:
        db.delete(profile)
    db.commit()
    return get_user_threshold_profiles(db, user_id)


def provision_threshold_profiles_from_json(db: Session, user_id: int, thresholds: dict, category: str = "default"):
    """
    Provision user threshold profiles from a JSON object.
    Handles nested blood pressure, normalizes enums, and commits efficiently.
    """
    if not thresholds or not isinstance(thresholds, dict):
        raise HTTPException(status_code=400, detail="Invalid thresholds JSON")

    created_profiles = []

    for vital_type, limits in thresholds.items():
        if vital_type == "blood_pressure" and isinstance(limits, dict):
            # Handle systolic and diastolic separately
            for bp_type in ["systolic", "diastolic"]:
                bp_limits = limits.get(bp_type)
                if not bp_limits:
                    continue
                low = bp_limits.get("low")
                high = bp_limits.get("high")
                if low is None or high is None:
                    continue
                profile = ThresholdProfile(
                    user_id=user_id,
                    category=ThresholdCategory.BLOOD_PRESSURE,
                    vital_type=f"blood_pressure_{bp_type}",
                    low=low,
                    high=high,
                    severity=ThresholdSeverity.LOW
                )
                db.add(profile)
                created_profiles.append(profile)
        else:
            # Regular vitals
            if not isinstance(limits, dict):
                continue
            low = limits.get("low")
            high = limits.get("high")
            if low is None or high is None:
                continue
            try:
                category_enum = ThresholdCategory[vital_type.upper()]
            except Exception:
                category_enum = ThresholdCategory.DEFAULT
            profile = ThresholdProfile(
                user_id=user_id,
                category=category_enum,
                vital_type=vital_type,
                low=low,
                high=high,
                severity=ThresholdSeverity.LOW
            )
            db.add(profile)
            created_profiles.append(profile)

    try:
        db.commit()
        for p in created_profiles:
            db.refresh(p)
    except Exception as e:
        db.rollback()
        logging.exception("Failed to commit threshold profiles: %s", e)
        raise HTTPException(status_code=500, detail="Failed to provision threshold profiles")

    return created_profiles

# ---------------------------- EFFECTIVE THRESHOLDS ----------------------------
def get_user_effective_thresholds(db: Session, user_id: int) -> Dict[str, Dict[str, float]]:
    """
    Returns the 'effective' threshold profiles for a user.
    Merges the user's custom thresholds (if any) with system defaults from threshold_defaults.json.
    Output is a JSON-serializable dict:
    {
        "heart_rate": {"low": 50.0, "high": 110.0},
        "oxygen_saturation": {"low": 95.0, "high": 100.0},
        ...
    }
    """
    try:
        # Load default thresholds from JSON
        defaults_json = THRESHOLDS_JSON.get("default", {})
        defaults: Dict[str, Dict[str, float]] = {}

        for vital, val in defaults_json.items():
            if vital == "blood_pressure":
                for bp_type, bp_val in val.items():
                    defaults[f"blood_pressure_{bp_type}"] = bp_val
            else:
                defaults[vital] = val

        # Load user-specific thresholds
        profiles = db.query(ThresholdProfile).filter(ThresholdProfile.user_id == user_id).all()
        merged: Dict[str, Dict[str, float]] = {}

        # Start with defaults
        for vital, val in defaults.items():
            merged[vital] = {
                "low": val.get("low"),
                "high": val.get("high")
            }

        # Overwrite with any user-specific customizations
        for p in profiles:
            vtype = getattr(p, "vital_type", None)
            if not vtype:
                continue
            merged[vtype] = {
                "low": p.low,
                "high": p.high
            }

        return merged

    except Exception as e:
        logging.exception("Failed to get effective thresholds for user_id=%s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch threshold profiles")


# ---------------------------- REFRESH TOKENS ----------------------------
def create_refresh_token_record(db: Session, user_id: int, jti: str, token: str, expires_at: datetime):
    db_rt = RefreshToken(user_id=user_id, jti=jti, token=token, expires_at=expires_at, revoked=False)
    db.add(db_rt)
    db.commit()
    db.refresh(db_rt)
    return db_rt


def get_refresh_token_by_jti(db: Session, jti: str):
    return db.query(RefreshToken).filter(RefreshToken.jti == jti).first()


def revoke_refresh_token(db: Session, jti: str):
    rt = get_refresh_token_by_jti(db, jti)
    if rt:
        rt.revoked = True
        db.commit()
        db.refresh(rt)
    return rt


def revoke_all_user_refresh_tokens(db: Session, user_id: int):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False
    ).update({RefreshToken.revoked: True}, synchronize_session=False)
    db.commit()


# ---------------------------- THRESHOLD SIMULATION ----------------------------
def simulate_threshold_breach(db: Session, user_id: int):
    vitals = [
        "heart_rate", "oxygen_saturation", "temperature",
        "respiratory_rate", "blood_pressure_systolic", "blood_pressure_diastolic"
    ]
    vital = random.choice(vitals)
    severity_str = random.choice([ThresholdSeverity.HIGH.value, ThresholdSeverity.LOW.value])
    threshold = get_threshold_range(db, user_id, vital)
    if not threshold:
        raise HTTPException(status_code=404, detail=f"No threshold found for {vital}")

    if severity_str == ThresholdSeverity.HIGH.value:
        value = (threshold["high"] or 0) + random.uniform(1, 15)
    else:
        value = (threshold["low"] or 0) - random.uniform(1, 15)

    health_data_payload = {v: None for v in vitals}
    health_data_payload[vital] = value
    health_data_payload["user_id"] = user_id
    health_data_payload["device_id"] = 1  # Assign default device_id if exists
    health_data_payload["timestamp"] = datetime.now(timezone.utc)

    try:
        health_data = HealthData(**health_data_payload)
        db.add(health_data)
        db.commit()
        db.refresh(health_data)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to simulate health data: {e}")

    try:
        severity_enum = ThresholdSeverity(severity_str)
        alert_event = AlertEventCreate(
            user_id=user_id,
            health_data_id=health_data.id,
            vital_type=vital,
            value=value,
            severity=severity_enum,
            timestamp=datetime.now(timezone.utc),
            resolved=False
        )
        db_alert = AlertEvent(**alert_event.model_dump())
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        try:
            dispatch_alert(db_alert)
        except Exception as e:
            logging.warning(f"⚠️ Failed to dispatch simulated alert: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create alert event: {e}")

    return {"health_data": health_data, "alert": db_alert}
