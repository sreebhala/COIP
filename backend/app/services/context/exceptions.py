class AppointmentRequestNotFoundError(Exception):
    """Raised when the referenced appointment_request_id does not exist.
    Maps to HTTP 404. No context is fabricated in this case."""


class EmergencyRoutingRequiredError(Exception):
    """Raised when an appointment request has emergency_flag_entered_by_staff
    set to true. This is a hard safety stop, not a normal validation failure:
    the Context Builder halts immediately and no downstream data (schedule,
    queue, resource, attendance) is gathered. COIP never evaluates or routes
    the emergency itself — staff must use the clinic's approved emergency
    process outside this system."""

    def __init__(self, appointment_request_id: str):
        self.appointment_request_id = appointment_request_id
        super().__init__(
            f"Appointment request {appointment_request_id} is flagged as an "
            "emergency by staff. COIP does not process this request. Use "
            "the clinic's approved emergency workflow."
        )
