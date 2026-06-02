"""
Tests for POST /forgot-password and POST /reset-password endpoints.

Pattern: follows test_auth_rate_limit.py (direct AsyncClient + ASGITransport,
dependency_overrides for DB and EmailSender, no conftest fixtures needed for
rate-limit tests).

For token-lifecycle tests we use the db_test + async_client fixtures from conftest.py
which provide a real isolated transaction against kitchy_test.
"""

import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from main import app
from app.core.database import get_db
from app.routers.auth import get_email_sender
from app.services.email.base import EmailSender
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.core.security import get_password_hash, verify_password

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FORGOT_URL = "/api/v1/auth/forgot-password"
RESET_URL = "/api/v1/auth/reset-password"
UNIFORM_MSG = "If that email is registered, you will receive a reset link shortly."


def _mock_email_sender() -> EmailSender:
    """Returns an EmailSender mock with a tracked async send_reset_email."""
    sender = MagicMock(spec=EmailSender)
    sender.send_reset_email = AsyncMock()
    return sender


class MockEmptyResult:
    """DB execute result that returns no rows."""
    def scalars(self):
        class _Scalars:
            def first(self):
                return None
        return _Scalars()


# ---------------------------------------------------------------------------
# 7.1 Anti-enumeration: unknown email → 200, no email sent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_unknown_email_returns_200_no_email():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockEmptyResult())
    mock_sender = _mock_email_sender()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_email_sender] = lambda: mock_sender

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(FORGOT_URL, json={"email": "nobody@example.com"})

        assert response.status_code == 200
        assert response.json()["message"] == UNIFORM_MSG
        mock_sender.send_reset_email.assert_not_called()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 7.2 Anti-enumeration: inactive account → 200, no email sent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_inactive_user_returns_200_no_email(db_test):
    from app.core.security import get_password_hash

    inactive_user = User(
        email="inactive@kitchy.com",
        hashed_password=get_password_hash("irrelevant123"),
        plan="free",
        is_active=False,
    )
    db_test.add(inactive_user)
    await db_test.flush()

    mock_sender = _mock_email_sender()
    app.dependency_overrides[get_email_sender] = lambda: mock_sender

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(FORGOT_URL, json={"email": "inactive@kitchy.com"})

        assert response.status_code == 200
        assert response.json()["message"] == UNIFORM_MSG
        mock_sender.send_reset_email.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_email_sender, None)


# ---------------------------------------------------------------------------
# 7.3 Token generation and hash storage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_generation_and_hash_storage(db_test, test_user):
    from sqlalchemy.future import select
    from app.core.config import settings

    mock_sender = _mock_email_sender()
    app.dependency_overrides[get_email_sender] = lambda: mock_sender

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(FORGOT_URL, json={"email": test_user["email"]})

        assert response.status_code == 200
        mock_sender.send_reset_email.assert_called_once()

        # Inspect what was actually persisted
        result = await db_test.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == test_user["user_object"].id
            )
        )
        token_row = result.scalars().first()

        assert token_row is not None, "Expected a token row in the DB"
        assert token_row.used is False

        # Verify the call args: reset_link contains the plain token
        call_args = mock_sender.send_reset_email.call_args
        reset_link: str = call_args[0][1]  # positional arg 1
        plain_token = reset_link.split("?token=")[1]

        # token_hash must equal sha256(plain_token)
        expected_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        assert token_row.token_hash == expected_hash, "token_hash must be sha256 of plain token"

        # Plain token must NOT be stored in the DB row
        assert plain_token not in (token_row.token_hash,), "Plain token must not equal the stored hash"

        # expires_at ≈ now + TTL (within 5-second tolerance)
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES)
        delta = abs((token_row.expires_at - expected_expiry).total_seconds())
        assert delta < 5, f"expires_at deviation too large: {delta}s"
    finally:
        app.dependency_overrides.pop(get_email_sender, None)


# ---------------------------------------------------------------------------
# 7.4 Previous token invalidated on new request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_previous_token_invalidated_on_new_request(db_test, test_user):
    from sqlalchemy.future import select

    # Insert a "pending" token (T1) manually
    t1_plain = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    t1_hash = hashlib.sha256(t1_plain.encode()).hexdigest()
    t1 = PasswordResetToken(
        user_id=test_user["user_object"].id,
        token_hash=t1_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used=False,
    )
    db_test.add(t1)
    await db_test.flush()

    mock_sender = _mock_email_sender()
    app.dependency_overrides[get_email_sender] = lambda: mock_sender

    try:
        # Trigger a new reset → T1 should be invalidated, T2 created
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(FORGOT_URL, json={"email": test_user["email"]})

        assert response.status_code == 200

        # Refresh T1
        await db_test.refresh(t1)
        assert t1.used is True, "T1 should have been marked used=True"

        # Only the new token (T2) is valid
        result = await db_test.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == test_user["user_object"].id,
                PasswordResetToken.used == False,  # noqa: E712
            )
        )
        valid_tokens = result.scalars().all()
        assert len(valid_tokens) == 1, "Only T2 should be valid"
        assert valid_tokens[0].token_hash != t1_hash
    finally:
        app.dependency_overrides.pop(get_email_sender, None)


# ---------------------------------------------------------------------------
# 7.5 Expired token rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_token_rejected(db_test, test_user):
    plain_token = "expiredtokenvalue_expiredtokenvalue_expiredtoken"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    expired_token = PasswordResetToken(
        user_id=test_user["user_object"].id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        used=False,
    )
    db_test.add(expired_token)
    await db_test.flush()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(RESET_URL, json={
            "token": plain_token,
            "new_password": "newpassword123",
        })

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


# ---------------------------------------------------------------------------
# 7.6 Already-used token rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_used_token_rejected(db_test, test_user):
    plain_token = "usedtokenvalue_usedtokenvalue_usedtokenvalue_u"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    used_token = PasswordResetToken(
        user_id=test_user["user_object"].id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used=True,
    )
    db_test.add(used_token)
    await db_test.flush()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(RESET_URL, json={
            "token": plain_token,
            "new_password": "newpassword123",
        })

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired reset token."


# ---------------------------------------------------------------------------
# 7.7 Successful password reset
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_password_reset(db_test, test_user):
    from sqlalchemy.future import select

    plain_token = "validtokenvalue_validtokenvalue_validtokenvalue"
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    valid_token = PasswordResetToken(
        user_id=test_user["user_object"].id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used=False,
    )
    db_test.add(valid_token)
    await db_test.flush()

    new_password = "supersecure99"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(RESET_URL, json={
            "token": plain_token,
            "new_password": new_password,
        })

    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully."

    # Verify the DB was updated
    result = await db_test.execute(
        select(User).where(User.id == test_user["user_object"].id)
    )
    updated_user = result.scalars().first()
    assert verify_password(new_password, updated_user.hashed_password), \
        "Password should have been updated in the DB"

    # Token must be marked used
    await db_test.refresh(valid_token)
    assert valid_token.used is True


# ---------------------------------------------------------------------------
# 7.8 Rate limit on /forgot-password (3/minute)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_rate_limit():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockEmptyResult())
    mock_sender = _mock_email_sender()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_email_sender] = lambda: mock_sender

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First 3 requests must be allowed (returning 200, user not found → no email)
            for i in range(3):
                r = await ac.post(FORGOT_URL, json={"email": f"user{i}@example.com"})
                assert r.status_code == 200, f"Request {i+1} should be 200, got {r.status_code}"

            # 4th request must be rate-limited
            r = await ac.post(FORGOT_URL, json={"email": "user4@example.com"})
            assert r.status_code == 429, f"Expected 429 on 4th request, got {r.status_code}"

        # Email must have been called at most 3 times (0 in this case since user not found)
        assert mock_sender.send_reset_email.call_count <= 3
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 7.9 Rate limit on /reset-password (5/minute)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_rate_limit():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockEmptyResult())

    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First 5 requests allowed (400 because token not found, but NOT rate-limited)
            for i in range(5):
                r = await ac.post(RESET_URL, json={
                    "token": f"invalidtoken{i}",
                    "new_password": "password123",
                })
                assert r.status_code == 400, f"Request {i+1} should be 400, got {r.status_code}"

            # 6th request must be rate-limited
            r = await ac.post(RESET_URL, json={
                "token": "invalidtoken6",
                "new_password": "password123",
            })
            assert r.status_code == 429, f"Expected 429 on 6th request, got {r.status_code}"
    finally:
        app.dependency_overrides.clear()
