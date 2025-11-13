from pydantic import BaseModel
from typing import Dict, Optional
from backend.schemas.enums import Gender, HealthContext

class OnboardingRequest(BaseModel):
    age: int
    activity_level: str
    chronic_condition: bool
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[Gender] = None
    health_context: Optional[HealthContext] = None

class OnboardingResponse(BaseModel):
    user_id: int
    assigned_category: str
    thresholds: Dict[str, Dict[str, float]]
    created_profiles_count: int

