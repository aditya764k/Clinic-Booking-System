"""
Import all models here so that:
1. Alembic autogenerate can discover them via Base.metadata
2. SQLAlchemy can resolve all cross-model relationships
"""
from app.models.identity import User, PatientProfile, DoctorProfile  # noqa: F401
from app.models.scheduling import AppointmentSlot                      # noqa: F401
from app.models.appointment import Appointment, ClinicalNote           # noqa: F401
from app.models.billing import Invoice, WebhookEvent                   # noqa: F401
from app.models.audit import AuditLog                                  # noqa: F401
