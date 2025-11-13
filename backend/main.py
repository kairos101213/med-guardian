# main.py
from fastapi import FastAPI
from fastapi.routing import APIRoute
from contextlib import asynccontextmanager
from backend.database import database
from backend.routers import (
    user,
    device,
    health_data,
    emergency_contacts,
    alerts,
    emergencies,
    thresholds,
    auth,
    ping,
    onboarding,
    sos
)
from backend.models.models import (
    User,
    UserProfile,
    Device,
    HealthData,
    EmergencyContact,
    Emergency,
    ThresholdDefault,
    ThresholdProfile,
    AlertEvent,
    AlertNotification,
    RefreshToken,
    SOSRequest
)

from backend.utils.security import get_password_hash
from backend.schemas.enums import UserRole
import os

# ---------------- Lifespan context ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    Creates all tables on startup, prints registered routes,
    and ensures a default admin user exists.
    """
    # Create all tables
    database.Base.metadata.create_all(bind=database.engine)

    # Ensure default admin exists
    db = database.SessionLocal()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@domain.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")  # use env var in production
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        hashed_password = get_password_hash(admin_password)
        admin_user = User(
            name="Admin User",
            email=admin_email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"✅ Default admin created: {admin_email}")
    else:
        print(f"ℹ️ Admin already exists: {admin_email}")
    db.close()

    # Print registered routes
    print("📌 ROUTES REGISTERED:")
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ",".join(route.methods)
            print(f"{methods:10} -> {route.path}")
    
    yield

# ---------------- FastAPI instance ----------------
app = FastAPI(lifespan=lifespan)

# ---------------- Include routers ----------------
app.include_router(user.router)
app.include_router(device.router)
app.include_router(health_data.router)
app.include_router(emergency_contacts.router)
app.include_router(alerts.router)
app.include_router(emergencies.router)
app.include_router(thresholds.router)
app.include_router(auth.router)
app.include_router(ping.router)
app.include_router(onboarding.router)  
app.include_router(sos.router)







