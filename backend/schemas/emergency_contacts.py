from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ------------------ EMERGENCY CONTACT ------------------
class EmergencyContactBase(BaseModel):
    name: str
    phone_number: str
    relation_type: Optional[str] = None

class EmergencyContactCreate(EmergencyContactBase):
    user_id: Optional[int] = None  # Only admins can specify; normal users ignore

class EmergencyContactUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    relation_type: Optional[str] = None

class EmergencyContactOut(EmergencyContactBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ------------------ EMERGENCY ------------------
class EmergencyBase(BaseModel):
    user_id: int
    device_id: Optional[int] = None
    emergency_type: str
    severity: str
    description: Optional[str] = None
    timestamp: Optional[datetime] = None

class EmergencyCreate(EmergencyBase):
    pass

class EmergencyUpdate(BaseModel):
    emergency_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    resolved: Optional[bool] = None

class EmergencyOut(EmergencyBase):
    id: int
    resolved: bool

    class Config:
        from_attributes = True
