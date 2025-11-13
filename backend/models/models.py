from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database.database import Base
from backend.schemas.enums import (
    UserRole, Gender, HealthContext,
    ThresholdCategory, ThresholdSeverity,
    AlertMethod, AlertStatus, SOSStatus
)

# ---------- USER ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    email_verified = Column(Boolean, nullable=False, default=False)  

    devices = relationship("Device", back_populates="owner", cascade="all, delete-orphan")
    health_data = relationship("HealthData", back_populates="user", cascade="all, delete-orphan")
    emergency_contacts = relationship("EmergencyContact", back_populates="user", cascade="all, delete-orphan")
    emergencies = relationship("Emergency", back_populates="user", cascade="all, delete-orphan")
    threshold_profiles = relationship("ThresholdProfile", back_populates="user", cascade="all, delete-orphan")
    alert_events = relationship("AlertEvent", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sos_requests = relationship("SOSRequest", back_populates="user", cascade="all, delete-orphan")
    email_otps = relationship("EmailOTP", back_populates="user", cascade="all, delete-orphan")


# ---------- USER PROFILE ----------
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    age = Column(Integer, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)
    chronic_condition = Column(Boolean, nullable=True, default=False)
    activity_level = Column(String, nullable=True)
    health_context = Column(SQLEnum(HealthContext), nullable=True)

    user = relationship("User", back_populates="profile")


# ---------- DEVICE ----------
class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fcm_token = Column(String, nullable=True)

    owner = relationship("User", back_populates="devices")
    health_data = relationship("HealthData", back_populates="device", cascade="all, delete-orphan")
    emergencies = relationship("Emergency", back_populates="device", cascade="all, delete-orphan")
    sos_requests = relationship("SOSRequest", back_populates="device", cascade="all, delete-orphan")


# ---------- HEALTH DATA ----------
class HealthData(Base):
    __tablename__ = "health_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    heart_rate = Column(Float, nullable=False)
    blood_pressure_systolic = Column(Float, nullable=False)
    blood_pressure_diastolic = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)
    oxygen_saturation = Column(Float, nullable=False)
    respiratory_rate = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="health_data")
    device = relationship("Device", back_populates="health_data")
    alert_event = relationship("AlertEvent", back_populates="health_data", uselist=False, cascade="all, delete-orphan")


# ---------- EMERGENCY CONTACT ----------
class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    relation_type = Column(String, nullable=True)

    user = relationship("User", back_populates="emergency_contacts")


# ---------- EMERGENCY ----------
class Emergency(Base):
    __tablename__ = "emergencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    alert_event_id = Column(Integer, ForeignKey("alert_events.id"), nullable=True)  # 🔥 NEW
    emergency_type = Column(String, nullable=False)
    severity = Column(SQLEnum(ThresholdSeverity), nullable=False, index=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved = Column(Boolean, default=False)

    user = relationship("User", back_populates="emergencies")
    device = relationship("Device", back_populates="emergencies")
    alert_event = relationship("AlertEvent")  


# ---------- THRESHOLDS ----------
class ThresholdDefault(Base):
    __tablename__ = "threshold_defaults"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(SQLEnum(ThresholdCategory), nullable=False)
    vital_type = Column(String, nullable=False)
    low = Column(Float, nullable=False)
    high = Column(Float, nullable=False)


class ThresholdProfile(Base):
    __tablename__ = "threshold_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(SQLEnum(ThresholdCategory), nullable=False, default=ThresholdCategory.CUSTOMIZABLE)
    vital_type = Column(String, nullable=False)
    low = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    severity = Column(SQLEnum(ThresholdSeverity), nullable=False, default=ThresholdSeverity.LOW)

    user = relationship("User", back_populates="threshold_profiles")

# ---------- ALERT EVENT ----------
class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    health_data_id = Column(Integer, ForeignKey("health_data.id"), nullable=True)
    vital_type = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    severity = Column(SQLEnum(ThresholdSeverity), nullable=False, index=True)
    message = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    vitals_snapshot = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved = Column(Boolean, default=False)

    user = relationship("User", back_populates="alert_events")
    health_data = relationship("HealthData", back_populates="alert_event")
    notifications = relationship("AlertNotification", back_populates="alert_event", cascade="all, delete-orphan")
    sos_requests = relationship("SOSRequest", back_populates="alert_event", cascade="all, delete-orphan")


# ---------- ALERT NOTIFICATION ----------
class AlertNotification(Base):
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, index=True)
    alert_event_id = Column(Integer, ForeignKey("alert_events.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("emergency_contacts.id"), nullable=True)  # 🔥 NEW
    method = Column(SQLEnum(AlertMethod), nullable=False)
    recipient = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING, nullable=False, index=True)

    alert_event = relationship("AlertEvent", back_populates="notifications")
    contact = relationship("EmergencyContact")


# ---------- REFRESH TOKEN ----------
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    jti = Column(String, unique=True, nullable=False)
    token = Column(String(512), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


# ---------- SOS REQUEST ----------
class SOSRequest(Base):
    __tablename__ = "sos_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_event_id = Column(Integer, ForeignKey("alert_events.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    severity = Column(SQLEnum(ThresholdSeverity), default=ThresholdSeverity.HIGH, nullable=False, index=True)
    status = Column(SQLEnum(SOSStatus), default=SOSStatus.PENDING, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    dispatched = Column(Boolean, default=False, index=True)
    vitals_snapshot = Column(String, nullable=True)  # optional context
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="sos_requests")
    alert_event = relationship("AlertEvent", back_populates="sos_requests")
    device = relationship("Device", back_populates="sos_requests")

# ---------- EMAIL OTP ---------- 
class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    purpose = Column(String, default="email_verification", nullable=False)
    sent_via = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    user = relationship("User", back_populates="email_otps")
