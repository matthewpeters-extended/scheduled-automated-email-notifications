from app.config import settings
from app.mail.base import Mailer
from app.mail.mock_mailer import MockMailer
from app.mail.smtp_mailer import SmtpMailer


def get_mailer() -> Mailer:
    return SmtpMailer() if settings.mail_mode == "live" else MockMailer()
