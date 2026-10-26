from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.email import Email
from app.models import EmailStatus, ScheduledEmail, User
from app.schemas import PaginatedScheduledEmails, ScheduleEmailRequest, ScheduledEmailOut

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("", response_model=ScheduledEmailOut, status_code=status.HTTP_201_CREATED)
def schedule_email(
    payload: ScheduleEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    email = Email.scheduleEmail(
        db,
        user_id=current_user.id,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body=payload.body,
        scheduled_time=payload.scheduled_time,
    )
    return email.scheduled_email


@router.get("", response_model=PaginatedScheduledEmails)
def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: EmailStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ScheduledEmail).filter(ScheduledEmail.user_id == current_user.id)
    if status_filter:
        query = query.filter(ScheduledEmail.status == status_filter)

    total = query.count()
    items = query.order_by(ScheduledEmail.scheduled_time.desc()).offset(skip).limit(limit).all()
    return PaginatedScheduledEmails(total=total, skip=skip, limit=limit, items=items)


@router.get("/{email_id}", response_model=ScheduledEmailOut)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    email = (
        db.query(ScheduledEmail)
        .filter(ScheduledEmail.id == email_id, ScheduledEmail.user_id == current_user.id)
        .first()
    )
    if email is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheduled email not found")
    return email


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_email(
    email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    email = (
        db.query(ScheduledEmail)
        .filter(ScheduledEmail.id == email_id, ScheduledEmail.user_id == current_user.id)
        .first()
    )
    if email is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheduled email not found")
    if email.status != EmailStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a pending email can be canceled")

    db.delete(email)
    db.commit()
