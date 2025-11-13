# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any, Dict
import logging

from backend.database.database import get_db
from backend.models.models import User
from backend.schemas import auth as auth_schemas
from backend.schemas import tokens as token_schemas
from backend.schemas.user import UserOut, UserProfileCreate, UserProfileOut
from backend.schemas.otp import (
    GenerateEmailOTPRequest,
    ResendEmailOTPRequest,
    VerifyEmailOTPRequest,
)
from backend.crud import crud
from backend.utils import security
from backend.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------- REGISTER ----------------
@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def register(payload: auth_schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user and send OTP for email verification.
    """
    existing_user = crud.get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        user = crud.create_user_with_password(db, payload)
    except Exception as e:
        logger.exception("Failed to create user: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Send OTP via SendGrid
    try:
        otp_result = crud.generate_and_send_email_otp(db, user.id, to_email=user.email)
    except Exception as e:
        logger.exception("Failed to send OTP: %s", e)
        otp_result = {"sent": False}

    return {
        "user_id": user.id,
        "message": "Account created. Please verify your email before logging in.",
        "otp_sent": otp_result.get("sent", False),
        # "dev_plaintext_otp": otp_result.get("dev_plaintext_otp"), for dev only
    }


# ---------------- RESEND EMAIL OTP ----------------
@router.post("/resend-email-otp", status_code=status.HTTP_200_OK)
def api_resend_email_otp(payload: ResendEmailOTPRequest, request: Request, db: Session = Depends(get_db)):
    """
    Resend email OTP using CRUD function.
    Payload: { "email": "<user_email>" }
    """
    email = payload.email.strip() if payload.email else None
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    result = crud.resend_email_otp(db, email=email, ip_address=ip_address, user_agent=user_agent)
    return result


# ---------------- VERIFY EMAIL ----------------
@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_email(payload: VerifyEmailOTPRequest, db: Session = Depends(get_db)):
    """
    Verify an email OTP (body: { user_id, code }).
    On success, sets user.email_verified = True.
    """
    try:
        result = crud.verify_email_otp(db, payload.user_id, payload.code.strip())
    except Exception as e:
        logger.exception("Error verifying OTP: %s", e)
        raise HTTPException(status_code=500, detail="Verification failed")

    if not result.get("ok"):
        reason = result.get("reason", "invalid")
        if reason == "no_valid_code":
            raise HTTPException(status_code=400, detail="No valid code found (expired or not requested)")
        if reason == "max_attempts_exceeded":
            raise HTTPException(status_code=400, detail="Too many incorrect attempts. Request a new code.")
        if reason == "invalid_code":
            raise HTTPException(status_code=400, detail=f"Invalid code. Attempts left: {result.get('attempts_left', 0)}")
        raise HTTPException(status_code=400, detail="Invalid verification code")

    return {"message": "Email verified successfully. Please log in."}


# ---------------- LOGIN ----------------
@router.post("/login", response_model=token_schemas.TokenPair)
def login(request: auth_schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, request.email)
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not security.verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Ensure email verified
    if not getattr(user, "email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified. Please verify your email first.")

    # Generate tokens
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    refresh_token, jti, exp = security.create_refresh_token(
        data={"sub": user.email, "role": user.role.value}
    )
    crud.create_refresh_token_record(db, user_id=user.id, jti=jti, token=refresh_token, expires_at=exp)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# ---------------- CURRENT USER ----------------
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------- ONBOARDING PROFILE ----------------
@router.post("/onboarding/profile", response_model=UserProfileOut)
def onboarding(
    profile: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create or update user's profile without threshold provisioning.
    """
    return crud.create_user_profile(db, user_id=current_user.id, profile=profile)


# ---------------- REFRESH TOKEN ----------------
@router.post("/refresh", response_model=token_schemas.Token)
def refresh_token(req: auth_schemas.RefreshRequest, db: Session = Depends(get_db)):
    payload = security.decode_refresh_token(req.refresh_token)
    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        raise HTTPException(status_code=401, detail="Invalid refresh payload")

    rt = crud.get_refresh_token_by_jti(db, jti)
    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    user = crud.get_user_by_email(db, sub)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------- LOGOUT ----------------
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    crud.revoke_all_user_refresh_tokens(db, current_user.id)
    return
