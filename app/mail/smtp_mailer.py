import smtplib
from email.mime.text import MIMEText

from app.config import settings
from app.mail.base import Mailer


class SmtpMailer(Mailer):
    """Real delivery via SMTP (STARTTLS), using the SMTP_* settings from
    .env. Works as-is against Gmail's SMTP relay, Mailtrap's sandbox, or any
    standard SMTP provider."""

    def send(self, to: str, subject: str, body: str) -> None:
        if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
            raise RuntimeError("SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD are not fully set")

        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = settings.smtp_from_email
        message["To"] = to

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to], message.as_string())
