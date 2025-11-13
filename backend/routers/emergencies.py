from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from backend.database.database import get_db
from backend.models.models import Emergency
from backend.schemas.emergency_contacts import EmergencyCreate, EmergencyOut, EmergencyUpdate
from backend.utils.security import get_current_user
from backend.models.models import User
from backend.schemas.enums import UserRole
from backend.crud import crud

router = APIRouter(
    prefix="/emergencies",
    tags=["Emergencies"],
    dependencies=[Depends(get_current_user)]
)

# ---------------- CREATE EMERGENCY ----------------
@router.post("/", response_model=EmergencyOut)
def create_emergency(
    emergency: EmergencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new emergency record. Users can only create for themselves; admins can specify any user."""
    payload = emergency.model_dump(exclude_unset=True)
    if current_user.role != UserRole.ADMIN:
        payload["user_id"] = current_user.id

    db_emergency = crud.create_emergency(db, payload)
    return db_emergency


# ---------------- GET EMERGENCIES ----------------
@router.get("/", response_model=List[EmergencyOut])
def get_all_emergencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all emergencies. Admins see all; users see only their own."""
    if current_user.role == UserRole.ADMIN:
        return crud.get_all_emergencies(db)
    return crud.get_user_emergencies(db, current_user.id)


@router.get("/user/{user_id}", response_model=List[EmergencyOut])
def get_user_emergencies(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve emergencies for a specific user. Users can only access their own emergencies."""
    if current_user.role != UserRole.ADMIN and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return crud.get_user_emergencies(db, user_id)


# ---------------- UPDATE EMERGENCY ----------------
@router.put("/{emergency_id}", response_model=EmergencyOut)
def update_emergency(
    emergency_id: int,
    emergency_update: EmergencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing emergency record. Only owner or admin can update."""
    db_emergency = crud.get_emergency_by_id(db, emergency_id)
    if not db_emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if db_emergency.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    updated = crud.update_emergency(db, emergency_id, emergency_update)
    return updated


# ---------------- DELETE EMERGENCY ----------------
@router.delete("/{emergency_id}")
def delete_emergency(
    emergency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an emergency record. Only owner or admin can delete."""
    db_emergency = crud.get_emergency_by_id(db, emergency_id)
    if not db_emergency:
        raise HTTPException(status_code=404, detail="Emergency not found")
    if db_emergency.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    crud.delete_emergency(db, emergency_id)
    return {"message": "Emergency deleted successfully"}


