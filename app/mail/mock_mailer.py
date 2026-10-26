import json
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.mail.base import Mailer


class MockMailer(Mailer):
    """Appends a JSON line per "sent" email to a local outbox file instead
    of touching a real SMTP server. Addresses whose local part starts with
    "bounce-" always raise, which is what lets the retry/attempts logic be
    tested deterministically without a real flaky mail server. (A sentinel
    domain like ".test" would be tidier, but email_validator correctly
    rejects reserved special-use TLDs, so the sentinel lives in the local
    part instead, on an otherwise ordinary domain.)"""

    def send(self, to: str, subject: str, body: str) -> None:
        if to.split("@")[0].startswith("bounce-"):
            raise RuntimeError(f"simulated delivery failure for {to}")

        record = {
            "to": to,
            "subject": subject,
            "body": body,
            "sent_at": datetime.utcnow().isoformat(),
        }
        path = Path(settings.mock_outbox_path)
        with path.open("a") as f:
            f.write(json.dumps(record) + "\n")
