from abc import ABC, abstractmethod


class Mailer(ABC):
    """The only contract the rest of the app depends on. Implementations
    either really send mail (SmtpMailer) or fake it (MockMailer) — callers
    can't tell which from the interface."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        """Raise on failure. Returning normally means "delivered."""
        raise NotImplementedError
