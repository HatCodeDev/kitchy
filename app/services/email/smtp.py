import aiosmtplib
from email.message import EmailMessage

from app.services.email.base import EmailSender
from app.core.config import settings


class SmtpEmailSender(EmailSender):
    async def send_reset_email(self, to_email: str, reset_link: str) -> None:
        message = EmailMessage()
        message["From"] = settings.MAIL_FROM
        message["To"] = to_email
        message["Subject"] = "Reset your Kitchy password"
        message.set_content(
            f"Click the link to reset your password:\n{reset_link}\n\n"
            f"This link expires in {settings.RESET_TOKEN_TTL_MINUTES} minutes. "
            f"If you did not request this, ignore it."
        )
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
