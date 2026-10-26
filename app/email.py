from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.mail.base import Mailer
from app.mail.registry import get_mailer
from app.models import EmailStatus, ScheduledEmail


class Email:
    """Domain object wrapping one ScheduledEmail row. Method names
    (scheduleEmail/sendEmail) intentionally mirror the task spec's wording
    rather than PEP 8's snake_case, since the spec names them explicitly as
    the OOP requirement this class exists to satisfy."""

    def __init__(self, db: Session, scheduled_email: ScheduledEmail):
        self.db = db
        self.scheduled_email = scheduled_email

    @classmethod
    def scheduleEmail(
        cls,
        db: Session,
        user_id: int,
        recipient_email: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
    ) -> "Email":
        row = ScheduledEmail(
            user_id=user_id,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            scheduled_time=scheduled_time,
            status=EmailStatus.pending,
            attempts=0,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return cls(db, row)

    def sendEmail(self, mailer: Mailer | None = None) -> bool:
        """Attempts delivery once. On failure, increments attempts and
        leaves status=pending (so the cron job retries it next run) unless
        MAIL_MAX_ATTEMPTS has been reached, at which point it gives up and
        marks the email failed. Returns whether this attempt succeeded."""
        mailer = mailer or get_mailer()
        row = self.scheduled_email
        now = datetime.utcnow()

        try:
            mailer.send(row.recipient_email, row.subject, row.body)
        except Exception as exc:
            row.attempts += 1
            row.last_attempt_at = now
            row.last_error = str(exc)
            if row.attempts >= settings.mail_max_attempts:
                row.status = EmailStatus.failed
            self.db.commit()
            return False
        else:
            row.attempts += 1
            row.last_attempt_at = now
            row.last_error = None
            row.status = EmailStatus.sent
            row.sent_at = now
            self.db.commit()
            return True
