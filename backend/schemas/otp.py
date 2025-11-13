# backend/schemas/otp.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class GenerateEmailOTPRequest(BaseModel):
    user_id: int

class ResendEmailOTPRequest(BaseModel):
    email: EmailStr

class VerifyEmailOTPRequest(BaseModel):
    user_id: int
    code: str = Field(..., min_length=4, max_length=10)  # numeric 6-digit expected but allow flexible length

class EmailOTPOut(BaseModel):
    id: int
    user_id: int
    created_at: Optional[datetime]
    expires_at: Optional[datetime]
    used: bool
    attempts: int
    purpose: str

    model_config = {"from_attributes": True}
