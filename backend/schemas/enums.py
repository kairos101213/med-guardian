from enum import Enum

# ------------------ SEVERITY ------------------
class ThresholdSeverity(str, Enum):
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"

# ------------------ ALERT ------------------
class AlertMethod(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"

class AlertStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

# ------------------ USER ROLES ------------------
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

# ------------------ THRESHOLD CATEGORY ------------------
class ThresholdCategory(str, Enum):
    DEFAULT = "default"

    # Base categories
    ELDERLY = "elderly"
    ATHLETE = "athlete"
    CHRONIC = "chronic"
    CUSTOMIZABLE = "customizable"

    # Elderly subcategories
    elderly_60s = "elderly_60s"
    elderly_70s = "elderly_70s"
    elderly_80s = "elderly_80s"

    # Athlete subcategories
    athlete_young = "athlete_young"
    athlete_adult= "athlete_adult"
    athlete_senior = "athlete_senior"

    # Chronic subcategories
    chronic_young = "chronic_young"
    chronic_adult = "chronic_adult"
    chronic_senior = "chronic_senior"

# ------------------ GENDER ------------------
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

# ------------------ HEALTH CONTEXT ------------------
class HealthContext(str, Enum):
    DEFAULT = "default"
    ELDERLY = "elderly"
    ATHLETE = "athlete"
    CHRONIC = "chronic"

# ------------------ SOS STATUS ------------------
class SOSStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"
