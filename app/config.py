from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "mock" writes sent mail to a local outbox file so the app works with
    # zero SMTP credentials. "live" sends through real SMTP using the
    # settings below. Nothing else in the codebase changes between the two.
    mail_mode: str = "mock"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@example.com"

    mock_outbox_path: str = "outbox.jsonl"

    session_secret: str = "dev-secret-change-me"
    cron_interval_seconds: int = 30
    mail_max_attempts: int = 3


settings = Settings()
