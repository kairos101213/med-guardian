from pydantic import BaseModel
from typing import Optional, Dict
from backend.schemas.enums import ThresholdCategory, ThresholdSeverity

# ----- Threshold Defaults -----
class ThresholdDefaultBase(BaseModel):
    vital_type: str
    low: Optional[float] = None
    high: Optional[float] = None

class ThresholdDefaultCreate(ThresholdDefaultBase):
    pass

class ThresholdDefaultOut(ThresholdDefaultBase):
    id: int
    class Config:
        from_attributes = True


# ----- Threshold Profiles -----
class ThresholdProfileBase(BaseModel):
    vital_type: str
    low: Optional[float] = None
    high: Optional[float] = None
    category: ThresholdCategory = ThresholdCategory.DEFAULT
    severity: ThresholdSeverity = ThresholdSeverity.LOW

class ThresholdProfileCreate(ThresholdProfileBase):
    user_id: int

class ThresholdProfileOut(ThresholdProfileBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True


# ----- Custom Thresholds -----
class ThresholdValueIn(BaseModel):
    low: Optional[float] = None
    high: Optional[float] = None

class CustomThresholdsIn(BaseModel):
    thresholds: Dict[str, ThresholdValueIn]
    user_id: Optional[int] = None

