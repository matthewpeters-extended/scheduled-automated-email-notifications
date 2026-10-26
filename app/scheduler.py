from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.cron import process_due_emails
from app.database import SessionLocal

scheduler = BackgroundScheduler()


def _run_cron_job():
    db = SessionLocal()
    try:
        process_due_emails(db)
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            _run_cron_job,
            "interval",
            seconds=settings.cron_interval_seconds,
            id="process_due_emails",
            replace_existing=True,
        )
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
