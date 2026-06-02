import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email.base import EmailSender

logger = logging.getLogger(__name__)


class InvalidTokenError(Exception):
    """Raised when the provided reset token is invalid, expired, or already used."""
    pass


class PasswordResetService:

    async def request_reset(
        self,
        db: AsyncSession,
        email_sender: EmailSender,
        email: str,
        client_ip: str = "unknown",
    ) -> None:
        """
        Initiates the password reset flow for the given email.
        Returns silently regardless of whether the email exists (anti-enumeration).
        """
        email_hash = hashlib.sha256(email.encode()).hexdigest()

        # Look up the user
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

        if user is None:
            logger.warning(
                "Forgot-password attempt for unknown email",
                extra={"email_hash": email_hash, "ip": client_ip},
            )
            return

        if not user.is_active:
            logger.warning(
                "Forgot-password attempt for inactive account",
                extra={"user_id": str(user.id), "ip": client_ip},
            )
            return

        # Invalidate any existing pending tokens for this user
        now = datetime.now(timezone.utc)
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,  # noqa: E712
                PasswordResetToken.expires_at > now,
            )
            .values(used=True)
        )

        # Generate a new plain token and store its hash
        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        new_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES),
            used=False,
        )
        db.add(new_token)
        # Persist the token (and the prior-token invalidation) BEFORE sending the
        # email. get_db() does not auto-commit, so without this the token would be
        # rolled back on session close and every reset would fail.
        await db.commit()

        reset_link = f"{settings.RESET_LINK_BASE_URL}?token={plain_token}"

        try:
            await email_sender.send_reset_email(user.email, reset_link)
        except Exception:
            logger.exception(
                "Failed to send password reset email",
                extra={"user_id": str(user.id), "ip": client_ip},
            )
            # Do NOT re-raise — SMTP failures must not leak to the client

    async def reset_password(
        self,
        db: AsyncSession,
        token: str,
        new_password: str,
    ) -> None:
        """
        Validates the reset token and updates the user's password.
        Raises InvalidTokenError if the token is invalid, used, or expired.
        """
        digest = hashlib.sha256(token.encode()).hexdigest()

        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == digest)
        )
        token_row = result.scalars().first()

        if token_row is None:
            raise InvalidTokenError("Token not found")

        if token_row.used:
            raise InvalidTokenError("Token already used")

        now = datetime.now(timezone.utc)
        if token_row.expires_at <= now:
            raise InvalidTokenError("Token expired")

        # Update the user's password
        result = await db.execute(select(User).where(User.id == token_row.user_id))
        user = result.scalars().first()

        user.hashed_password = get_password_hash(new_password)
        token_row.used = True

        await db.commit()


password_reset_service = PasswordResetService()
