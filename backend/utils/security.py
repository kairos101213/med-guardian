import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend import crud
from backend.schemas.enums import UserRole
from backend.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger("security")

# ---------- Password Hashing ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as exc:
        # Avoid bubbling internal errors as 500; log and return False
        logger.warning("Password verification failed: %s", exc)
        return False


# ---------- Time Helpers ----------
def _utcnow() -> datetime:
    """Return current UTC time with timezone."""
    return datetime.now(timezone.utc)


# ---------- Token Management ----------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = _utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "iat": _utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    jti: Optional[str] = None,
    expires_minutes: int = REFRESH_TOKEN_EXPIRE_MINUTES
) -> tuple[str, str, datetime]:
    """Create a JWT refresh token with unique jti."""
    to_encode = data.copy()
    jti = jti or str(uuid.uuid4())
    expire = _utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "iat": _utcnow(), "jti": jti})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti, expire


def decode_access_token(token: str) -> dict:
    """Decode a JWT access token. Raises 401 if invalid/expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired access token")


def decode_refresh_token(token: str) -> dict:
    """Decode a JWT refresh token. Raises 401 if invalid/expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired refresh token")


# ---------- Role normalization helpers ----------
def _role_to_str(role) -> str:
    """
    Normalizes role value to a lowercase string.

    Accepts: UserRole enum, enum members, raw strings.
    Returns: 'user', 'admin', etc. or empty string if unknown.
    """
    if role is None:
        return ""
    # If it's an instance of our UserRole (or any Enum with .value)
    try:
        # If it's a UserRole enum:
        if isinstance(role, UserRole):
            return role.value.lower()
    except Exception:
        pass

    # If it has .value attribute (other enum), try that
    val = getattr(role, "value", None)
    if isinstance(val, str):
        return val.lower()

    # Fallback to string
    try:
        return str(role).lower()
    except Exception:
        return ""


# ---------- FastAPI Dependencies ----------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Extract the current user from an access token."""
    payload = decode_access_token(token)
    email = payload.get("sub")
    token_role = payload.get("role")

    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token payload")

    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Optional: compare token role to DB role and log mismatch (do not block)
    token_role_norm = _role_to_str(token_role)
    db_role_norm = _role_to_str(getattr(user, "role", None))
    if token_role_norm and db_role_norm and token_role_norm != db_role_norm:
        logger.warning("Token role (%s) differs from DB role (%s) for user %s", token_role_norm, db_role_norm, email)

    return user


def require_roles(*roles: UserRole) -> Callable:
    """
    FastAPI dependency to enforce user roles.

    Usage:
        Depends(require_roles(UserRole.ADMIN))
    """
    allowed = [r.value.lower() if isinstance(r, UserRole) else str(r).lower() for r in roles]

    def _enforcer(user=Depends(get_current_user)):
        user_role_norm = _role_to_str(getattr(user, "role", None))
        # If no allowed roles were provided, allow anyone
        if allowed and user_role_norm not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Insufficient permissions")
        return user
    return _enforcer

