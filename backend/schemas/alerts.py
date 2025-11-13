from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.schemas.enums import ThresholdSeverity, AlertMethod, AlertStatus, SOSStatus

# ---------------- ALERT EVENT ----------------
class AlertEventBase(BaseModel):
    user_id: int
    user_name: Optional[str] = None 
    health_data_id: Optional[int] = None
    vital_type: str
    value: float
    severity: ThresholdSeverity
    timestamp: Optional[datetime] = None
    resolved: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vitals_snapshot: Optional[str] = None
    message: Optional[str] = None

class AlertEventCreate(AlertEventBase):
    pass

class AlertEventOut(AlertEventBase):
    id: int
    model_config = {"from_attributes": True}


# ---------------- ALERT NOTIFICATION ----------------
class AlertNotificationBase(BaseModel):
    alert_event_id: int
    method: AlertMethod
    status: AlertStatus = AlertStatus.PENDING
    timestamp: Optional[datetime] = None
    recipient: Optional[str] = None
    message: Optional[str] = None

class AlertNotificationCreate(AlertNotificationBase):
    contact_id: Optional[int] = None

class AlertNotificationOut(AlertNotificationBase):
    id: int
    model_config = {"from_attributes": True}


# ---------------- SOS ----------------
class SOSRequestBase(BaseModel):
    user_id: int
    device_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    severity: ThresholdSeverity = ThresholdSeverity.HIGH
    status: SOSStatus = SOSStatus.PENDING
    dispatched: bool = False
    timestamp: Optional[datetime] = None
    vitals_snapshot: Optional[str] = None  # optional for context

class SOSRequestCreate(SOSRequestBase):
    pass

class SOSRequestOut(SOSRequestBase):
    id: int
    alert_event_id: int
    model_config = {"from_attributes": True}


# ---------------- THRESHOLD CHECK/UTIL MODELS ----------------
class ThresholdCheckResult(BaseModel):
    vital_type: str
    value: float
    severity: ThresholdSeverity

class ThresholdCheckResponse(BaseModel):
    user_id: int
    health_data_id: Optional[int] = None
    alerts: List[ThresholdCheckResult]
    model_config = {"from_attributes": True}

