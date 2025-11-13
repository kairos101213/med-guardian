from pydantic import BaseModel, Field
from typing import List, Optional
from backend.schemas.enums import Gender, UserRole

# ------------------ USER CREATION ------------------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str  

# ------------------ USER UPDATE ------------------
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None  # optional password update

# ------------------ USER OUTPUT ------------------
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: Optional[UserRole] = UserRole.USER
    email_verified: bool = False

    class Config:
        from_attributes = True

# ------------------ USER PROFILE (Onboarding) ------------------
class UserProfileCreate(BaseModel):
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[Gender] = None
    chronic_condition: Optional[bool] = False
    activity_level: Optional[str] = "normal"
    health_context: Optional[str] = None

class UserProfileOut(BaseModel):
    id: int
    user_id: int
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[Gender] = None
    chronic_condition: Optional[bool] = False
    activity_level: Optional[str] = None
    health_context: Optional[str] = None

    class Config:
        from_attributes = True

