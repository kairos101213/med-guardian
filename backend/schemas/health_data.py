# schemas/health_data.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# ------------------ CREATE ------------------
class HealthDataCreate(BaseModel):
    device_id: int
    heart_rate: float
    blood_pressure_systolic: float
    blood_pressure_diastolic: float
    temperature: Optional[float] = None
    oxygen_saturation: float
    respiratory_rate: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None

# ------------------ RESPONSE ------------------
class HealthDataResponse(HealthDataCreate):
    id: int

    class Config:
        from_attributes = True 


# ------------------ UPDATE ------------------
class HealthDataUpdate(BaseModel):
    heart_rate: Optional[float] = None
    blood_pressure_systolic: Optional[float] = None
    blood_pressure_diastolic: Optional[float] = None
    oxygen_saturation: Optional[float] = None
    temperature: Optional[float] = None
    respiratory_rate: Optional[float] = None
    timestamp: Optional[datetime] = None
