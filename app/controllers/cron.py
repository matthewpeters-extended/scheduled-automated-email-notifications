from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.cron import process_due_emails
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import CronRunResult

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/run", response_model=CronRunResult)
def run_cron(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Runs on a schedule (see app/scheduler.py) but any logged-in user can
    also trigger it on demand — useful for demos and for the mock-mode
    walkthrough in the README."""
    return process_due_emails(db)
