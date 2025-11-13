from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database.database import get_db
from backend.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate
from backend.crud import crud
from backend.utils.security import get_current_user
from backend.models.models import User
from backend.schemas.enums import UserRole

router = APIRouter(
    prefix="/devices",
    tags=["Devices"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

# ---------------- CREATE DEVICE ----------------
@router.post("/", response_model=DeviceOut)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new device.
    - Regular users: user_id is forced to their own.
    - Admins: can create devices for any user (must supply user_id).
    """
    # Admin can create device for any user
    if current_user.role == UserRole.ADMIN:
        if not device.user_id:
            raise HTTPException(status_code=400, detail="Admin must provide user_id")
        payload = device
    else:
        # Regular user: override user_id to current user
        payload = DeviceCreate(
            device_name=device.device_name,
            user_id=current_user.id
        )

    db_device = crud.create_device(db, payload)
    return db_device


# ---------------- GET DEVICES ----------------
@router.get("/", response_model=List[DeviceOut])
def get_devices(
    user_id: Optional[int] = Query(None, description="Filter by user_id (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List devices.
    - Admins: can see all devices or filter by user_id.
    - Regular users: only see their own devices (user_id query ignored).
    """
    if current_user.role == UserRole.ADMIN:
        devices = crud.get_devices(db, user_id=user_id)
    else:
        devices = crud.get_devices(db, user_id=current_user.id)

    return devices


# ---------------- GET SINGLE DEVICE ----------------
@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a single device by ID. Only owner or admin can access."""
    db_device = crud.get_device(db, device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    if db_device.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return db_device


# ---------------- UPDATE DEVICE ----------------
@router.put("/{device_id}", response_model=DeviceOut)
def update_device(
    device_id: int,
    updates: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a device. Only owner or admin can update."""
    db_device = crud.get_device(db, device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    if db_device.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Ensure that updates.user_id (if provided) is allowed
    if updates.user_id and updates.user_id != db_device.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Cannot reassign device")

    updated_device = crud.update_device(db, device_id, updates)
    return updated_device


# ---------------- DELETE DEVICE ----------------
@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a device. Only owner or admin can delete."""
    db_device = crud.get_device(db, device_id)
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    if db_device.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    crud.delete_device(db, device_id)
    return {"message": "Device deleted successfully"}


