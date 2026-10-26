from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.email import Email
from app.models import EmailStatus, ScheduledEmail
from app.schemas import CronRunResult


def process_due_emails(db: Session) -> CronRunResult:
    """Finds every pending email whose scheduled_time has passed and hasn't
    exhausted its retry budget, and attempts to send each one. Safe to call
    on any interval — an email already sent or already failed-out just
    won't match the filter again."""
    due = (
        db.query(ScheduledEmail)
        .filter(
            ScheduledEmail.status == EmailStatus.pending,
            ScheduledEmail.scheduled_time <= datetime.utcnow(),
            ScheduledEmail.attempts < settings.mail_max_attempts,
        )
        .all()
    )

    sent = 0
    failed = 0
    for row in due:
        if Email(db, row).sendEmail():
            sent += 1
        else:
            failed += 1

    return CronRunResult(mode=settings.mail_mode, checked=len(due), sent=sent, failed=failed)
