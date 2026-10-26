"""One-off: create a demo user and one already-due scheduled email, so
there's something to see immediately after `uvicorn app.main:app` starts
and the background cron job (or a manual POST /cron/run) fires."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.email import Email
from app.models import User
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

user = db.query(User).filter(User.email == "demo@email-notifications.dev").first()
if user:
    print("Demo user already exists.")
else:
    user = User(
        name="Demo User",
        email="demo@email-notifications.dev",
        password=hash_password("demo12345"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print("Created demo@email-notifications.dev / demo12345")

Email.scheduleEmail(
    db,
    user_id=user.id,
    recipient_email="someone@example.com",
    subject="Demo reminder",
    body="This was scheduled by the seed script, already due in the past.",
    scheduled_time=datetime.utcnow() - timedelta(minutes=1),
)
print("Scheduled one demo email, already due.")

db.close()
