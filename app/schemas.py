from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import EmailStatus


# --- Auth ------------------------------------------------------------------


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Scheduled emails --------------------------------------------------------


class ScheduleEmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    scheduled_time: datetime


class ScheduledEmailOut(BaseModel):
    id: int
    recipient_email: EmailStr
    subject: str
    body: str
    scheduled_time: datetime
    status: EmailStatus
    attempts: int
    last_error: str | None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedScheduledEmails(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[ScheduledEmailOut]


# --- Cron --------------------------------------------------------------------


class CronRunResult(BaseModel):
    mode: str
    checked: int
    sent: int
    failed: int
