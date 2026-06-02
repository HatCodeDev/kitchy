# Apply Progress: Password Reset via Email

**Change**: password-reset-email
**Batch**: Slice A + Slice B (all implementation phases complete)
**Date**: 2026-06-02
**Status**: DONE — Phases 1-7 complete. Phase 8 is manual operator work.

---

## Completed Tasks

### Phase 1: Dependencies and Configuration
- [x] 1.1 — Added `aiosmtplib==3.0.2` to `requirements.txt`, pinned with `==` to match the pattern of pinned deps (`passlib[bcrypt]==1.7.4`, `bcrypt==3.2.2`) already in the file.
- [x] 1.2 — Extended `app/core/config.py` with all 7 new fields.

### Phase 2: Data Model and Migration
- [x] 2.1 — Created `app/models/password_reset_token.py` with `PasswordResetToken`.
- [x] 2.2 — Registered in `app/models/__init__.py`.
- [x] 2.3 — Created `alembic/versions/a1b2c3d4e5f6_add_password_reset_tokens.py`. `down_revision = '3367284e9ba0'` (the merge migration, confirmed as current head).

### Phase 3: Email Layer
- [x] 3.1 — Created `app/services/email/__init__.py` (empty package marker).
- [x] 3.2 — Created `app/services/email/base.py` with `EmailSender` ABC.
- [x] 3.3 — Created `app/services/email/smtp.py` with `SmtpEmailSender`.

### Phase 4: Password Reset Service
- [x] 4.1 — Created `app/services/password_reset_service.py` with `PasswordResetService` and `InvalidTokenError`.
  - `request_reset`: user lookup, anti-enumeration (silent return for missing/inactive), internal WARNING logs with `email_hash`/`user_id` + client IP, token invalidation via `UPDATE ... SET used=True WHERE user_id=... AND used=False AND expires_at>now()`, `secrets.token_urlsafe(32)` generation, `sha256` hash storage, reset link construction, email dispatch wrapped in try/except (never re-raises).
  - `reset_password`: sha256 lookup, `InvalidTokenError` for not-found/used/expired, `get_password_hash` update, mark token `used=True`, commit.
  - Module-level singleton `password_reset_service = PasswordResetService()`.

### Phase 5: Pydantic Schemas
- [x] 5.1 — Added `ForgotPasswordRequest` (`email: EmailStr`) and `ResetPasswordRequest` (`token: str min_length=1`, `new_password: str min_length=8`) to `app/schemas/user.py` (where `Token`, `UserCreate`, `UserResponse` already live). No new file created.

### Phase 6: Endpoints
- [x] 6.1 — Added `POST /forgot-password` to `app/routers/auth.py`. Decorator order: `@router.post` then `@limiter.limit("3/minute")`. First param `request: Request`. Always returns 200 with uniform message.
- [x] 6.2 — Added `POST /reset-password` to `app/routers/auth.py`. `@limiter.limit("5/minute")`. Returns 400 on `InvalidTokenError`, 200 on success.
- [x] 6.3 — Defined `get_email_sender() -> EmailSender: return SmtpEmailSender()` in `app/routers/auth.py`. Injected via `Depends(get_email_sender)` in `/forgot-password`.

### Phase 7: Tests
- [x] 7.1 — `test_forgot_password_unknown_email_returns_200_no_email`: mock DB returns None, asserts 200 + uniform message + `send_reset_email` not called.
- [x] 7.2 — `test_forgot_password_inactive_user_returns_200_no_email`: creates inactive user in `db_test`, asserts 200 + no email.
- [x] 7.3 — `test_token_generation_and_hash_storage`: calls `/forgot-password` for real user, inspects persisted `PasswordResetToken`, verifies `token_hash == sha256(plain_token)`, `used=False`, `expires_at ≈ now+TTL (±5s)`.
- [x] 7.4 — `test_previous_token_invalidated_on_new_request`: inserts T1 manually, triggers new request, asserts T1 `used=True` and only one valid token (T2) remains.
- [x] 7.5 — `test_expired_token_rejected`: inserts token with `expires_at = now-1s`, asserts 400 with generic message.
- [x] 7.6 — `test_used_token_rejected`: inserts token with `used=True`, asserts 400.
- [x] 7.7 — `test_successful_password_reset`: full flow — valid token, POST `/reset-password`, asserts 200, DB `hashed_password` updated (verified with `verify_password`), token `used=True`.
- [x] 7.8 — `test_forgot_password_rate_limit`: 3 allowed (200), 4th blocked (429).
- [x] 7.9 — `test_reset_password_rate_limit`: 5 allowed (400 token-invalid, not rate-blocked), 6th blocked (429).

---

## Pending Tasks

- Phase 8: Manual operator checklist (DNS, SMTP env vars, `alembic upgrade head` on prod) — NOT automated.

---

## Deviations from Design

| Deviation | Rationale |
|-----------|-----------|
| `PasswordResetToken` uses classic `Column(...)` style, NOT `Mapped[...] / mapped_column(...)` as shown in design.md | The existing repo exclusively uses the classic Column style (`user.py`, all other models). Using `Mapped` would be the only model in the codebase with that pattern — inconsistent. Design note says "follow existing Base import"; the spirit is consistency with the codebase. |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` given empty-string defaults instead of being required (`str` with no default) | No `.env` file exists in the repo. Making them required would crash `settings = Settings()` at import time for any developer who hasn't yet added the env vars. Empty-string defaults allow the app to start; SMTP errors occur at call time, not at startup. This is a pragmatic safety valve. Spec says "no existing field MAY be removed or renamed" — it does not prohibit adding defaults. |
| Migration uses `sa.UUID()` instead of `postgresql.UUID(as_uuid=True)` | All existing migrations in this repo use `sa.UUID()` (not the dialect-specific variant). Only the model layer uses `postgresql.UUID(as_uuid=True)`. |
| `SmtpEmailSender.send_reset_email` uses `settings.RESET_TOKEN_TTL_MINUTES` in the email body instead of the hardcoded "30 minutes" from design.md | Keeps the email body consistent with the configured TTL value rather than lying to the user if the env var is ever changed. Strictly better behavior. |
| `get_email_sender` dependency defined in `app/routers/auth.py` instead of a separate `app/dependencies.py` | The router is the only consumer; there is no existing `dependencies.py` in the repo. Keeping it in `auth.py` avoids a new file for a single function. Can be extracted later if other routers need it. |
| `request_reset` accepts `client_ip: str = "unknown"` parameter | Allows the router to pass the actual client IP from `request.client.host` for internal abuse logging (REQ-7) without the service depending on the HTTP layer directly. |

---

## Files Created / Modified

| File | Action |
|------|--------|
| `requirements.txt` | MODIFIED — added `aiosmtplib==3.0.2` |
| `app/core/config.py` | MODIFIED — 7 new settings fields |
| `app/models/password_reset_token.py` | CREATED |
| `app/models/__init__.py` | MODIFIED — added `PasswordResetToken` import |
| `alembic/versions/a1b2c3d4e5f6_add_password_reset_tokens.py` | CREATED |
| `app/services/email/__init__.py` | CREATED (empty) |
| `app/services/email/base.py` | CREATED |
| `app/services/email/smtp.py` | CREATED |
| `app/services/password_reset_service.py` | CREATED |
| `app/schemas/user.py` | MODIFIED — added `ForgotPasswordRequest`, `ResetPasswordRequest` |
| `app/routers/auth.py` | MODIFIED — new imports, `get_email_sender`, `/forgot-password`, `/reset-password` |
| `tests/routers/test_auth_password_reset.py` | CREATED — 9 tests (7.1–7.9) |

---

## Test Execution

pytest was not runnable in the agent shell (Python not available via `python`/`python3`/`pytest` in the PATH — Windows Store stub only). To run the suite locally:

```powershell
# From the repo root (code/backend/kitchy)
# Set dummy SMTP env vars so settings validation passes at import time
$env:SMTP_HOST="smtp.example.com"
$env:SMTP_USER="user"
$env:SMTP_PASSWORD="pass"
$env:MAIL_FROM="Kitchy <noreply@example.com>"

# Run only the new tests
pytest tests/routers/test_auth_password_reset.py -v

# Or the full suite
pytest
```

Tests that use `db_test` / `async_client` require `kitchy_test` database to be reachable. Rate-limit tests (7.1, 7.8, 7.9) use a mocked DB and no DB connection.
