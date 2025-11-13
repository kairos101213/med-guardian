# schemas/token.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.schemas.enums import UserRole

# ------------------ ACCESS TOKEN ------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------ ACCESS + REFRESH TOKEN PAIR ------------------
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ------------------ TOKEN PAYLOAD ------------------
class TokenData(BaseModel):
    email: Optional[str] = None
    sub: Optional[str] = None
    role: Optional[UserRole] = None


# ------------------ USER INFO ------------------
class Me(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole

