from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    async def send_reset_email(self, to_email: str, reset_link: str) -> None:
        """Send a password reset email. Raises EmailSendError on failure."""
        ...
