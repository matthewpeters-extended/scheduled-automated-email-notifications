from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401  (import so Base knows about the tables)
from app.config import settings
from app.controllers import auth, cron, emails
from app.database import Base, engine
from app.deps import get_current_user
from app.limiter import limiter
from app.models import User
from app.scheduler import start_scheduler, stop_scheduler
from app.schemas import UserOut

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Automated Email Notification System", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(emails.router)
app.include_router(cron.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
