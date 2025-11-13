from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from backend.database.database import get_db
from backend.schemas.user import UserCreate, UserOut, UserUpdate
from backend.crud import crud
from backend.utils.security import get_current_user, require_roles, _role_to_str  # note: using normalization helper
from backend.schemas.enums import UserRole
from backend.models.models import User

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

# --------------------- Helpers ---------------------
def _ensure_self_or_admin(current_user: User, target_user_id: int):
    """Raise 403 unless current_user is admin or is the target user."""
    current_role = _role_to_str(getattr(current_user, "role", None))
    if current_role != UserRole.ADMIN.value and current_user.id != target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

# --------------------- Me (non-admin) ---------------------
@router.get("/me", response_model=UserOut)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return the current authenticated user's profile."""
    # Reuse standard get_user to include relationships as declared in UserOut
    db_user = crud.get_user(db, current_user.id)
    if not db_user:
        # Extremely unlikely unless user deleted after token issuance
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --------------------- Create (admin only) ---------------------
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(UserRole.ADMIN))])
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin route: Create a new user."""
    try:
        return crud.create_user(db, user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User with that email already exists")

# --------------------- List (admin only) ---------------------
@router.get("/", response_model=List[UserOut], dependencies=[Depends(require_roles(UserRole.ADMIN))])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all users (admin only)."""
    return crud.get_users(db)

# --------------------- Get single (self or admin) ---------------------
@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a single user (self or admin)."""
    _ensure_self_or_admin(current_user, user_id)
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --------------------- Update (self or admin) ---------------------
@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user information (self or admin)."""
    _ensure_self_or_admin(current_user, user_id)

    updated_user = crud.update_user(db, user_id, updates)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# --------------------- Delete (self or admin; protect admins) ---------------------
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a user:
      - Admin can delete anyone EXCEPT admin accounts (to avoid bricking the system).
      - A normal user can delete themselves.
    """
    target = crud.get_user(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Protect admin accounts from deletion
    if _role_to_str(getattr(target, "role", None)) == UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin accounts cannot be deleted")

    # Allow self or admin
    current_role = _role_to_str(getattr(current_user, "role", None))
    if current_role != UserRole.ADMIN.value and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    deleted = crud.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return




