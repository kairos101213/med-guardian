from pydantic import BaseModel, EmailStr
from typing import Optional

# ---------------- REGISTER ----------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

# ---------------- LOGIN ----------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------- REFRESH TOKEN ----------------
class RefreshRequest(BaseModel):
    refresh_token: str
