from datetime import date
from pydantic import BaseModel, ConfigDict, Field

class AppointmentRequestCreate(BaseModel):
    request_code: str = Field(min_length=2, max_length=30)
    patient_id: str
    location_id: str
    requested_doctor_id: str | None = None
    appointment_type_id: str
    preferred_date: date
    preferred_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    flexibility_minutes: int = Field(default=0, ge=0, le=240)
    contact_channel: str | None = None
    confirmation_status: str = "pending"
    request_source: str = "phone"
    status: str = "pending"
    emergency_flag_entered_by_staff: bool = False

class AppointmentRequestRead(AppointmentRequestCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AppointmentRequestListResponse(BaseModel):
    items: list[AppointmentRequestRead]
    total: int
