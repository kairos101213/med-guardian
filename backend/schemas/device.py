# schemas/device.py
from pydantic import BaseModel
from typing import Optional

class DeviceBase(BaseModel):
    device_name: str
    user_id: int
    fcm_token: Optional[str] = None  

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    user_id: Optional[int] = None
    fcm_token: Optional[str] = None  

class DeviceOut(DeviceBase):
    id: int

    class Config:
        from_attributes = True
