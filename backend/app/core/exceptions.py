"""
Domain exceptions for the Clinic Appointment Manager.

Rules:
- IllegalTransitionError is the ONLY permitted way to signal an invalid
  appointment status change. Endpoints must NOT raise generic HTTPExceptions
  for transition failures — let the FastAPI handler in main.py convert it.
- AIDraftGenerationError is raised by generate_clinical_draft() whenever the
  Gemini call fails (timeout, API error, or malformed response). The FastAPI
  handler in main.py converts it to HTTP 502. The cause_type attribute lets
  callers distinguish the failure mode for logging and user-facing messages.
"""
from __future__ import annotations

from typing import Literal

from app.models.appointment import AppointmentStatus


class IllegalTransitionError(Exception):
    """Raised when a caller attempts an invalid appointment status transition.

    This is a domain-level exception. The FastAPI exception handler registered
    in app/main.py converts it to HTTP 409 with a structured JSON body.

    Attributes:
        current_status:   The appointment's current AppointmentStatus.
        attempted_status: The AppointmentStatus the caller tried to move to.
        appointment_id:   The primary key of the appointment.
    """

    def __init__(
        self,
        *,
        current_status: AppointmentStatus,
        attempted_status: AppointmentStatus,
        appointment_id: int,
    ) -> None:
        self.current_status = current_status
        self.attempted_status = attempted_status
        self.appointment_id = appointment_id
        super().__init__(str(self))

    def __str__(self) -> str:
        cur = (
            self.current_status.value
            if hasattr(self.current_status, "value")
            else str(self.current_status)
        )
        att = (
            self.attempted_status.value
            if hasattr(self.attempted_status, "value")
            else str(self.attempted_status)
        )
        return (
            f"Cannot transition appointment {self.appointment_id} "
            f"from '{cur}' to '{att}'"
        )


class AIDraftGenerationError(Exception):
    """Raised by generate_clinical_draft() when the Gemini call fails.

    The FastAPI handler in app/main.py converts this to HTTP 502.

    Attributes:
        cause_type: One of 'timeout', 'api_error', or 'malformed_response'.
        message:    Human-readable description of the failure.
    """

    def __init__(
        self,
        *,
        cause_type: Literal["timeout", "api_error", "malformed_response"],
        message: str,
    ) -> None:
        self.cause_type = cause_type
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"AI draft generation failed ({self.cause_type}): {self.message}"
