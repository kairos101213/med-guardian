from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database.database import get_db
from backend.crud import crud
from backend.schemas import emergency_contacts as schema
from backend.utils.security import get_current_user
from backend.models.models import User
from backend.schemas.enums import UserRole

router = APIRouter(
    prefix="/emergency_contacts",
    tags=["Emergency Contacts"],
    dependencies=[Depends(get_current_user)]  
)

# ---------------- CREATE CONTACT ----------------
@router.post("/", response_model=schema.EmergencyContactOut, status_code=status.HTTP_201_CREATED)
def create_emergency_contact(
    contact: schema.EmergencyContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new emergency contact.
    - Users can only create contacts for themselves.
    - Admins can specify any user via `user_id`.
    """
    target_user_id = contact.user_id if current_user.role == UserRole.ADMIN and contact.user_id else current_user.id
    return crud.create_emergency_contact(db, contact, target_user_id)


# ---------------- GET ALL CONTACTS ----------------
@router.get("/", response_model=List[schema.EmergencyContactOut])
def get_all_emergency_contacts(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve emergency contacts.
    - Admins can query contacts for any user using `user_id`.
    - Regular users can only retrieve their own contacts.
    """
    query_user_id = user_id if current_user.role == UserRole.ADMIN and user_id else current_user.id
    return crud.get_all_emergency_contacts(db, query_user_id)


# ---------------- GET SINGLE CONTACT ----------------
@router.get("/{contact_id}", response_model=schema.EmergencyContactOut)
def get_emergency_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve a single emergency contact by ID.
    - Only the owner or an admin can access.
    """
    user_filter = None if current_user.role == UserRole.ADMIN else current_user.id
    return crud.get_emergency_contact(db, contact_id, user_filter)


# ---------------- UPDATE CONTACT ----------------
@router.put("/{contact_id}", response_model=schema.EmergencyContactOut)
def update_emergency_contact(
    contact_id: int,
    updates: schema.EmergencyContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing emergency contact.
    - Only the owner or an admin can update.
    """
    user_filter = None if current_user.role == UserRole.ADMIN else current_user.id
    return crud.update_emergency_contact(db, contact_id, user_filter, updates)


# ---------------- DELETE CONTACT ----------------
@router.delete("/{contact_id}", status_code=status.HTTP_200_OK)
def delete_emergency_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an emergency contact.
    - Only the owner or an admin can delete.
    """
    user_filter = None if current_user.role == UserRole.ADMIN else current_user.id
    crud.delete_emergency_contact(db, contact_id, user_filter)
    return {"detail": "Emergency contact deleted"}


